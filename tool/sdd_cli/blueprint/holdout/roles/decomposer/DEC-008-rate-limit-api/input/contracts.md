# CON-0040: Rate-Limit-Header und Fehlerformat

Jede Antwort unter `/v1/`:

| Header                  | Wert                                            |
|-------------------------|-------------------------------------------------|
| `X-RateLimit-Limit`     | `burst` des Schlüssels (Ganzzahl)               |
| `X-RateLimit-Remaining` | verbleibende ganze Tokens nach dieser Anfrage   |

Abgelehnte Anfrage: Status `429 Too Many Requests`, Header `Retry-After` = Sekunden bis zum
nächsten Token, aufgerundet auf eine Ganzzahl ≥ 1, Körper (`application/json`):

```json
{"error": "rate_limited", "retry_after": 2}
```

Anfragen ohne `X-Api-Key` werden wie bisher von der Authentifizierung mit 401 abgewiesen, bevor
das Limit greift.
