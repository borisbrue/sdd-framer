# CON-0031: Webhook-Nutzlast (behavior/markdown)

## Anfrage

`POST <url>` mit `Content-Type: application/json`.

Header:
| Header        | Inhalt                                                        |
|---------------|---------------------------------------------------------------|
| `X-Event-Id`  | ID aus `events.id`, bei Wiederholungen unverändert            |
| `X-Timestamp` | Unix-Sekunden des Versuchs (nicht des Ereignisses)            |
| `X-Signature` | `sha256=` + Hex-HMAC-SHA256(secret, `<X-Timestamp>.<body>`)   |

Körper:
```json
{"id": "evt_123", "type": "order.paid", "created_at": "2026-03-01T12:00:00Z",
 "data": {"order_id": "ord_9", "amount_cents": 4999, "currency": "EUR"}}
```

## Invarianten

- INV-01: Der Körper wird einmal serialisiert und byte-identisch signiert und gesendet.
- INV-02: Das Geheimnis erscheint nie in Logs oder in `deliveries`.
