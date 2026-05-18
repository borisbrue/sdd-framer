# Constraints

> Rahmenbedingungen, die für ALLE Specs gelten. Eine Spec darf hiervon nur per ADR abweichen.

## Technische Constraints

- **Sprachen/Stacks:** ...
- **Hosting:** ...
- **Datenbanken:** ...
- **Externe Dienste:** ...

## Sicherheits-Constraints

- Verschlüsselung: <z.B. TLS 1.3 in Transit, AES-256 at Rest>
- Authentifizierung: <z.B. OAuth2 / OIDC>
- Geheimnisse: <z.B. Vault, nie im Repo>

## Datenschutz / Compliance

- DSGVO: ...
- Datenresidenz: ...
- Aufbewahrungsfristen: ...

## Performance-Budgets (global)

- Initiale Ladezeit: < ...
- API p95: < ...

## Accessibility

- Mindestens WCAG 2.1 AA

## Browser-/Plattform-Support

- ...

## Organisatorisch

- Code-Owner-Reviews: Pflicht
- CI muss vor Merge grün sein
- Specs müssen Status `approved` haben, bevor Code gemergt wird
