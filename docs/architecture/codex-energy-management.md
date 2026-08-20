# Codex Energy Management

Codex is the current supervisory analysis and engineering agent. It is not a
continuous controller and not an electrical safety component.

## Interfaces

- OpenHAB REST/API for live state and explicitly authorized bounded actions.
- PostgreSQL for reproducible quantitative queries.
- CLI/systemd/journald for service and scheduler evidence.
- Repository source for implementation truth and version control.
- Hexmem for durable semantic context.

## Session lifecycle

1. Retrieve private Hexmem context.
2. Read this repository's canonical documents.
3. Inspect current source and live state for drift-prone facts.
4. Plan changes with explicit ownership, authority, evidence, and rollback.
5. Back up and validate before any authorized production write.
6. Verify the actual outcome.
7. Record only durable decisions, corrections, and conclusions in Hexmem.

## Boundaries

- Memory never authorizes action.
- Stale telemetry cannot authorize action.
- UI status is presentation, not safety authority.
- AI unavailability must not stop telemetry, deterministic automation, or
  electrical protection.
- Routine timer output belongs in PostgreSQL, journald, or reports.
- Physical actions and charge/protection changes require separate explicit
  approval and current-state validation.

## Future portability

A future in-house model should reuse the same OpenHAB contracts, PostgreSQL
schema/views, Markdown runbooks, and provider-neutral Hexmem records. Important
semantics must not exist only in a prompt or UI component.

Named review commands, structured-event handling, and the provider-neutral
Hexmem capture contract are documented in
`docs/operations/codex-review-workflows.md`.
