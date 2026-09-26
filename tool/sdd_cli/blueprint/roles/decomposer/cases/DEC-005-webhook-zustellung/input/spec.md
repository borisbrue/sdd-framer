---
id: SPEC-0047
title: Webhook-Zustellung für Bestellereignisse
status: approved
---

# SPEC-0047: Webhook-Zustellung für Bestellereignisse

## 1. Kontext

Der Shop-Kern erzeugt Ereignisse (`order.created`, `order.paid`, `order.shipped`) und legt sie
in der Tabelle `events` ab (vorhanden, Modul `shop/events.py`). Partner sollen diese Ereignisse
per HTTP-POST an eine eigene URL erhalten. Die Zustellung läuft als eigener Prozess
`python3 -m webhooks.worker`, der die Tabelle `events` abfragt. Das Format der Nutzlast und
der Header ist in CON-0031 festgelegt.

## 2. Begriffe

- **Abonnement:** Ziel-URL, Geheimnis (`secret`) und Liste der Ereignistypen eines Partners.
- **Zustellversuch:** ein einzelner HTTP-POST eines Ereignisses an ein Abonnement.

## 3. Funktionale Anforderungen

- **FR-01:** Abonnements werden in der Tabelle `subscriptions` gespeichert (`id`, `url`,
  `secret`, `event_types`, `active`). Das Kommando `python3 -m webhooks.admin add URL
  --events order.paid,order.shipped` legt ein Abonnement an und gibt das erzeugte Geheimnis
  einmalig aus; `deactivate ID` schaltet es ab. Die URL muss `https://` verwenden.
- **FR-02:** Jede Zustellung trägt den Header `X-Signature: sha256=<hex>`, den HMAC-SHA256
  über `<X-Timestamp>.<Rohkörper>` mit dem Geheimnis des Abonnements, sowie `X-Timestamp`
  (Unix-Sekunden) und `X-Event-Id` (die ID des Ereignisses, für Idempotenz beim Empfänger).
- **FR-03:** Antwortet der Empfänger nicht mit einem 2xx-Status innerhalb von 10 Sekunden,
  wird der Versuch wiederholt: bis zu 5 Wiederholungen mit Wartezeiten 30 s, 2 min, 10 min,
  1 h, 6 h. Jeder Versuch wird mit Zeitpunkt, Status und Dauer in `deliveries` protokolliert.
- **FR-04:** Nach der letzten erfolglosen Wiederholung wird die Zustellung als `dead` markiert
  und nicht weiter versucht. `python3 -m webhooks.admin redeliver EVENT_ID SUB_ID` setzt eine
  tote Zustellung zurück und startet die Wiederholungsfolge neu.
- **FR-05:** Ein 410-Status des Empfängers deaktiviert das Abonnement sofort (`active = 0`),
  ohne weitere Wiederholungen; offene Zustellungen dieses Abonnements werden als `dead`
  markiert.
- **FR-06:** Innerhalb eines Abonnements werden Ereignisse in der Reihenfolge ihrer Entstehung
  zugestellt: Ein Ereignis wird erst versucht, wenn alle älteren Ereignisse desselben
  Abonnements erfolgreich zugestellt oder `dead` sind. Verschiedene Abonnements blockieren
  einander nicht.

## 4. Nicht-Ziele

- Keine Web-Oberfläche zur Verwaltung von Abonnements.
- Kein Empfang eingehender Webhooks von Partnern.
- Keine anderen Transportwege als HTTPS (keine Queues, keine E-Mail).
