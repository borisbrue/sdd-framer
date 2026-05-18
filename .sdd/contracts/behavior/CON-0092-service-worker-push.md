---
id: CON-0092
title: "service-worker-push"
type: behavior
format: gherkin
spec: SPEC-0024
version: 0.1.0
status: draft
tests: [TST-0102]
---

# Contract: Service Worker Push-Handler

> **Spec:** SPEC-0024 · **Typ:** Behavior (Gherkin) · **Status:** draft

## Zweck

Definiert das Verhalten des Service Workers beim Empfang von Push-Notifications
sowie das Routing nach dem Tippen auf eine Notification.

**Abhängigkeit:** Der serverseitige Push-Trigger (Senden der Notification wenn
`orchestrate_done`) wird in SPEC-0023 definiert (CON-0075: `/api/sdd/run`
SSE-Output → Push-Broadcast). Dieser Contract definiert nur das Client-Verhalten.
(CF-0024-006 resolved)

## NotificationStrategy

| Zustand | Strategy |
|---|---|
| PWA im Vordergrund | `InAppStrategy` — Toast/Banner anzeigen, keine Systembenachrichtigung |
| PWA im Hintergrund | `WebPushStrategy` — Systembenachrichtigung via Push API |

## Szenarien

```gherkin
Feature: Service Worker Push-Handler

  Scenario: Orchestrate abgeschlossen — PWA im Hintergrund
    Given die PWA ist im Hintergrund (Service Worker aktiv)
    When eine Push-Notification mit payload {"type": "orchestrate_done", "spec_id": "SPEC-0024"} ankommt
    Then zeigt der Service Worker eine Systembenachrichtigung
    And die Notification hat title "SDD: Orchestrate abgeschlossen"
    And die Notification hat body "SPEC-0024 — Pipeline beendet"
    And die Notification hat data.url "/pwa/#/dashboard"

  Scenario: Notification-Tap öffnet PWA am richtigen Tab
    Given eine Systembenachrichtigung mit data.url "/pwa/#/logs/SPEC-0024" existiert
    When der Nutzer auf die Notification tippt
    Then öffnet der Service Worker die PWA
    And navigiert direkt zu /pwa/#/logs/SPEC-0024

  Scenario: Push-Permission — iOS Safari
    Given die PWA wird zum ersten Mal eingerichtet
    When der Setup-Flow erfolgreich abgeschlossen ist
    Then fragt die PWA nach Push-Notification-Berechtigung
    And zeigt eine Erklärung warum Push-Notifications hilfreich sind

  Scenario: PWA im Vordergrund — kein doppeltes Notifizieren
    Given die PWA ist aktiv im Vordergrund
    When eine Push-Notification ankommt
    Then zeigt der Service Worker KEINE Systembenachrichtigung
    And zeigt die PWA stattdessen einen In-App-Toast/Banner

  Scenario: Push-Subscription registrieren
    Given die Push-Permission ist erteilt
    When der Service Worker eine Push-Subscription erstellt
    Then sendet die PWA die Subscription an POST /api/push/subscribe
    And speichert die Subscription-ID in localStorage
```

## Payload-Format

Das Payload-Schema ist kanonisch in **CON-0077** (push-notification-payload) definiert.
Dieser Contract referenziert es nur zur Illustration. Bei Widersprüchen gilt CON-0077. (CF-0023-011 resolved)

```json
{
  "type": "orchestrate_done" | "build_done" | "build_failed" | "spec_implemented",
  "spec_id": "SPEC-XXXX",
  "message": "Menschenlesbare Zusammenfassung"
}
```
