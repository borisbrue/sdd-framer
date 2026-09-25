"""OpenAI-kompatibler Fake-Server für Pipeline-Tests (SPEC-0053).

Jede Rolle bekommt im Testprojekt ein eigenes Modell `fake-<rolle>`. Der Server beantwortet
`POST /v1/chat/completions` je Modell aus einer Warteschlange vorbereiteter Antworten und
zeichnet alle Anfragen auf. So laufen die Tests gegen die echte CLI, ohne `claude` oder ein
echtes Modell.
"""
from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


@dataclass
class Antwort:
    content: object
    finish_reason: str = "stop"
    prompt_tokens: int = 100
    completion_tokens: int = 50
    reasoning_tokens: int | None = None


@dataclass
class FakeLLM:
    antworten: dict[str, deque] = field(default_factory=lambda: defaultdict(deque))
    anfragen: list[dict] = field(default_factory=list)
    _server: ThreadingHTTPServer | None = None

    # ── Skript ──
    def antworte(self, rolle: str, *inhalte: object, **optionen: object) -> None:
        """Hängt Antworten für `fake-<rolle>` an.

        dicts/lists werden als JSON gesendet; eine Funktion bekommt die Anfrage und liefert den
        Inhalt (z. B. um eine task_id aus der Entscheidungsanfrage zu übernehmen).
        """
        for inhalt in inhalte:
            self.antworten[f"fake-{rolle}"].append(Antwort(inhalt, **optionen))

    def aufrufe(self, rolle: str) -> list[dict]:
        return [a for a in self.anfragen if a.get("model") == f"fake-{rolle}"]

    # ── Server ──
    @property
    def base_url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}/v1"

    def start(self) -> FakeLLM:
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                return

            def do_POST(self):
                laenge = int(self.headers.get("Content-Length", 0))
                anfrage = json.loads(self.rfile.read(laenge) or b"{}")
                fake.anfragen.append(anfrage)
                queue = fake.antworten.get(anfrage.get("model"))
                if not queue:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(b'{"error": {"message": "keine Antwort vorbereitet"}}')
                    return
                a = queue.popleft()
                inhalt = a.content(anfrage) if callable(a.content) else a.content
                if not isinstance(inhalt, str):
                    inhalt = json.dumps(inhalt, ensure_ascii=False)
                usage = {"prompt_tokens": a.prompt_tokens, "completion_tokens": a.completion_tokens,
                         "total_tokens": a.prompt_tokens + a.completion_tokens}
                if a.reasoning_tokens is not None:
                    usage["completion_tokens_details"] = {"reasoning_tokens": a.reasoning_tokens}
                body = json.dumps({
                    "id": f"fake-{len(fake.anfragen)}", "object": "chat.completion",
                    "created": int(time.time()), "model": anfrage.get("model"),
                    "choices": [{"index": 0, "finish_reason": a.finish_reason,
                                 "message": {"role": "assistant", "content": inhalt}}],
                    "usage": usage,
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()


def prompt_text(anfrage: dict) -> str:
    return "\n".join(str(m.get("content", "")) for m in anfrage.get("messages", []))


def task_id_aus(anfrage: dict) -> str:
    """task_id der offenen Entscheidungsanfrage, wie sie im Supervisor-Prompt steht."""
    import re

    treffer = re.search(r'"task_id"\s*:\s*"([^"]+)"', prompt_text(anfrage))
    return treffer.group(1) if treffer else "unbekannt"
