# language: de
Funktionalität: User Login
  Als registrierter Nutzer
  möchte ich mich mit E-Mail und Passwort einloggen
  um auf meine Daten zugreifen zu können

  Grundlage:
    Angenommen es existiert ein Nutzer mit E-Mail "alice@example.com" und Passwort "Correct-Horse-Battery"

  Szenario: Erfolgreicher Login
    Wenn ein POST /v1/auth/login mit gültigen Credentials gesendet wird
    Dann ist die Antwort HTTP 200
    Und der Body enthält die Felder "access_token", "refresh_token", "token_type", "expires_in"
    Und "token_type" ist "Bearer"
    Und "expires_in" ist 900
    Und "access_token" ist ein gültiges JWT mit Algorithmus "ES256"

  Szenario: Falsches Passwort
    Wenn ein POST /v1/auth/login mit korrekter E-Mail und falschem Passwort gesendet wird
    Dann ist die Antwort HTTP 401
    Und der Body enthält "code" mit Wert "invalid_credentials"
    Und der Body enthält keinen "access_token"

  Szenario: Nicht existierender Nutzer
    Wenn ein POST /v1/auth/login für "unbekannt@example.com" gesendet wird
    Dann ist die Antwort HTTP 401
    Und der Body enthält "code" mit Wert "invalid_credentials"
    # INV-01: ununterscheidbar vom Fall "falsches Passwort"

  Szenario: Account-Sperre nach 5 Fehlversuchen
    Wenn 5 fehlgeschlagene Login-Versuche für "alice@example.com" innerhalb von 15 Minuten erfolgen
    Und ein weiterer Login-Versuch für "alice@example.com" gesendet wird
    Dann ist die Antwort HTTP 423
    Und der Response-Header "Retry-After" ist gesetzt
    Und der Body enthält "code" mit Wert "account_locked"

  Szenariogrundriss: Validierungsfehler bei ungültigem Request
    Wenn ein POST /v1/auth/login mit <feld> = <wert> gesendet wird
    Dann ist die Antwort HTTP 400
    Und der Body enthält "code" mit Wert "validation_error"

    Beispiele:
      | feld     | wert                          |
      | email    | ""                            |
      | email    | "nicht-eine-email"            |
      | password | ""                            |
      | password | "<1025 Zeichen langer String>"|
