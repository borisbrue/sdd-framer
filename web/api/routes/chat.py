"""SPEC-0023: WebSocket /ws/chat.

CON-0074: Bearer-Auth (erste Frame oder HTTP-Header), Streaming-Tokens,
          Command-Output-Frames, IntentParser (Chain of Responsibility).
"""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import AsyncGenerator

import anthropic
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import sdd_context

router = APIRouter()

_CLOSE_UNAUTHORIZED = 4001
_MAX_HISTORY = 20
_MODEL = "claude-sonnet-4-6"
_SYSTEM_PROMPT = (
    "Du bist ein SDD-Assistent. Du kennst alle sdd-CLI-Commands: "
    "orchestrate, start, validate, dev, contract, spec, estimate. "
    "Du hilfst dem Nutzer, SDD-Specs zu erstellen und zu orchestrieren."
)

# Patched in tests
_exec = asyncio.create_subprocess_exec
_client_instance: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client_instance
    if _client_instance is None:
        _client_instance = anthropic.AsyncAnthropic()
    return _client_instance


# ── IntentParser — Chain of Responsibility ────────────────────────────────────

@dataclass
class ParsedIntent:
    cmd: str
    args: list[str]


class _IntentHandler:
    def __init__(self, successor: _IntentHandler | None = None) -> None:
        self._next = successor

    def handle(self, text: str) -> ParsedIntent | None:
        result = self._match(text.strip())
        if result is not None:
            return result
        return self._next.handle(text) if self._next else None

    def _match(self, text: str) -> ParsedIntent | None:
        return None


class _OrchestrateHandler(_IntentHandler):
    _PAT = re.compile(r"^orchestrate\s+(SPEC-\d{4})$", re.IGNORECASE)

    def _match(self, text: str) -> ParsedIntent | None:
        m = self._PAT.match(text)
        return ParsedIntent("orchestrate", ["--spec", m.group(1).upper()]) if m else None


class _StartHandler(_IntentHandler):
    _PAT = re.compile(r"^start\s+(SPEC-\d{4})$", re.IGNORECASE)

    def _match(self, text: str) -> ParsedIntent | None:
        m = self._PAT.match(text)
        return ParsedIntent("start", [m.group(1).upper()]) if m else None


class _DevBuildHandler(_IntentHandler):
    def _match(self, text: str) -> ParsedIntent | None:
        return ParsedIntent("dev", ["build"]) if text.lower() == "dev build" else None


class _DevUpHandler(_IntentHandler):
    def _match(self, text: str) -> ParsedIntent | None:
        return ParsedIntent("dev", ["up"]) if text.lower() == "dev up" else None


class _DevDownHandler(_IntentHandler):
    def _match(self, text: str) -> ParsedIntent | None:
        return ParsedIntent("dev", ["down"]) if text.lower() == "dev down" else None


class _StatusHandler(_IntentHandler):
    def _match(self, text: str) -> ParsedIntent | None:
        return ParsedIntent("validate", []) if text.lower() == "status" else None


def _build_parser() -> _IntentHandler:
    return _OrchestrateHandler(
        _StartHandler(
            _DevBuildHandler(
                _DevUpHandler(
                    _DevDownHandler(
                        _StatusHandler()
                    )
                )
            )
        )
    )


_intent_parser = _build_parser()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _run_cmd_lines(cmd: str, args: list[str]) -> AsyncGenerator[str, None]:
    proc = await _exec(
        "sdd", cmd, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    assert proc.stdout is not None
    async for raw in proc.stdout:
        yield raw.decode(errors="replace").rstrip()
    await proc.wait()


def _verify_ws_token(token: str) -> bool:
    if not token:
        return False
    try:
        config = sdd_context.get_config()
        expected = config.raw.get("pwa", {}).get("auth", {}).get("token", "")
        return bool(expected) and token == expected and not sdd_context.is_blacklisted(token)
    except Exception:
        return False


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket) -> None:
    await websocket.accept()

    auth_header = websocket.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        try:
            first_frame = await websocket.receive_json()
            token = first_frame.get("auth") or ""
        except Exception:
            await websocket.close(code=_CLOSE_UNAUTHORIZED)
            return

    if not _verify_ws_token(token):
        await websocket.close(code=_CLOSE_UNAUTHORIZED)
        return

    history: list[dict] = []

    try:
        while True:
            data = await websocket.receive_json()
            text = data.get("text")
            if not isinstance(text, str):
                continue

            intent = _intent_parser.handle(text)
            if intent:
                async for line in _run_cmd_lines(intent.cmd, intent.args):
                    await websocket.send_text(
                        json.dumps({"type": "command_output", "line": line})
                    )

            history.append({"role": "user", "content": text})

            reply = ""
            async with _get_client().messages.stream(
                model=_MODEL,
                max_tokens=2048,
                system=_SYSTEM_PROMPT,
                messages=history[-_MAX_HISTORY:],
            ) as stream:
                async for token_text in stream.text_stream:
                    reply += token_text
                    await websocket.send_text(json.dumps({"delta": token_text}))

            history.append({"role": "assistant", "content": reply})
            if len(history) > _MAX_HISTORY:
                history = history[-_MAX_HISTORY:]

            await websocket.send_text(json.dumps({"type": "done"}))

    except (WebSocketDisconnect, Exception):
        pass
