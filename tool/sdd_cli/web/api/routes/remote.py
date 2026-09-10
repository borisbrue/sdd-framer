"""SPEC-0023: POST /api/sdd/run (SSE) + POST /api/push/subscribe.

CON-0075: SddRunService — subprocess + SSE-Stream + PushStore-Trigger (Facade).
CON-0076: POST /api/push/subscribe — Dedup, VAPID-Check, 410-Invalidierung.
CON-0077: Push-Notification-Payload-Schema.
"""
from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import AsyncGenerator

import sdd_context
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pywebpush import WebPushException, webpush

router = APIRouter()

# Patched in tests via: patch("routes.remote._exec", ...)
_exec = asyncio.create_subprocess_exec

_PUSH_TRIGGER_CMDS = frozenset({"orchestrate", "dev"})
_ALLOWLIST = frozenset({"orchestrate", "start", "validate", "dev", "contract", "spec", "estimate"})


class PushStore:
    """Observer: In-Memory subscription registry. Deduplicates by endpoint."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subs: dict[str, dict] = {}

    def subscribe(self, sub: dict) -> None:
        with self._lock:
            self._subs[sub["endpoint"]] = sub

    def remove(self, endpoint: str) -> None:
        with self._lock:
            self._subs.pop(endpoint, None)

    def count(self) -> int:
        with self._lock:
            return len(self._subs)

    def broadcast(self, payload: dict, vapid_private_key: str, vapid_claims: dict) -> None:
        with self._lock:
            subs = list(self._subs.values())
        raw = json.dumps(payload, ensure_ascii=False)
        to_remove: list[str] = []
        for sub in subs:
            try:
                webpush(
                    subscription_info=sub,
                    data=raw,
                    vapid_private_key=vapid_private_key,
                    vapid_claims=vapid_claims,
                )
            except WebPushException as exc:
                if exc.response is not None and exc.response.status_code == 410:
                    to_remove.append(sub["endpoint"])
        for ep in to_remove:
            self.remove(ep)


_push_store = PushStore()


def _verify_bearer(request: Request) -> None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="invalid_token")
    token = header[7:]
    config = sdd_context.get_config()
    expected = config.raw.get("pwa", {}).get("auth", {}).get("token", "")
    if not expected or token != expected or sdd_context.is_blacklisted(token):
        raise HTTPException(status_code=401, detail="invalid_token")


def _vapid_cfg(config) -> tuple[str, dict] | None:
    vapid = config.raw.get("pwa", {}).get("vapid") or {}
    key = vapid.get("private_key", "")
    email = vapid.get("claims_email", "")
    if not key or not email:
        return None
    return key, {"sub": email}


class RunRequest(BaseModel):
    cmd: str
    args: list[str] = []


class SubscribeRequest(BaseModel):
    endpoint: str
    keys: dict


@router.post("/sdd/run")
async def sdd_run(body: RunRequest, request: Request) -> StreamingResponse:
    _verify_bearer(request)
    if body.cmd not in _ALLOWLIST:
        raise HTTPException(status_code=422, detail="unknown_command")

    config = sdd_context.get_config()
    push_trigger = body.cmd in _PUSH_TRIGGER_CMDS
    cmd, args = body.cmd, list(body.args)

    async def generate() -> AsyncGenerator[str, None]:
        proc = await _exec(
            "sdd", cmd, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        queue: asyncio.Queue[tuple[str, str] | None] = asyncio.Queue()

        async def drain(stream, name: str) -> None:
            async for raw in stream:
                await queue.put((name, raw.decode(errors="replace").rstrip()))
            await queue.put(None)

        t1 = asyncio.create_task(drain(proc.stdout, "stdout"))
        t2 = asyncio.create_task(drain(proc.stderr, "stderr"))

        done = 0
        while done < 2:
            item = await queue.get()
            if item is None:
                done += 1
            else:
                name, data = item
                yield f"data: {json.dumps({'type': 'line', 'data': data, 'stream': name})}\n\n"

        await asyncio.gather(t1, t2)
        exit_code = await proc.wait()
        yield f"data: {json.dumps({'type': 'done', 'exit_code': exit_code})}\n\n"

        if push_trigger:
            vapid = _vapid_cfg(config)
            if vapid:
                push_type = (
                    "build_failed" if exit_code != 0
                    else "orchestrate_done" if cmd == "orchestrate"
                    else "build_done"
                )
                spec_id = next((a for a in args if a.startswith("SPEC-")), "")
                payload = {
                    "type": push_type,
                    "spec_id": spec_id,
                    "message": (
                        f"{spec_id} — {cmd} fehlgeschlagen"
                        if exit_code != 0
                        else f"{spec_id} — {cmd} abgeschlossen"
                    ),
                }
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None, _push_store.broadcast, payload, vapid[0], vapid[1]
                )

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/push/subscribe", status_code=201)
async def push_subscribe(body: SubscribeRequest, request: Request) -> dict:
    _verify_bearer(request)
    config = sdd_context.get_config()
    if _vapid_cfg(config) is None:
        raise HTTPException(status_code=503, detail="vapid_not_configured")
    _push_store.subscribe({"endpoint": body.endpoint, "keys": body.keys})
    return {"subscribed": True}
