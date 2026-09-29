# Android contract compatibility implementation plan

> For agentic workers: use subagent-driven-development; preserve the independently scoped files below.

**Goal:** Restore compatibility with the existing LCTApp CURRENT_WORLD and analytics requests, without changing Android or inventing mastery policy.
**Architecture:** Extend existing FastAPI/domain/storage boundaries, preserve legacy JSON and idempotency digests, keep analytics independent of world backup, retain evidence across partial-history uploads.
**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy, PostgreSQL, Alembic, pytest, Ruff, ty.
**Spec:** [Backend mobile contract](../../mobile-contract.md); approved scope is Android audit B1–B4, excluding mastery policy.

## Global constraints
- User explicitly approved local checkout, backend changes and a GitHub PR. No production writes, deploy or merge.
- Game Kotlin DTOs and current wire examples are authoritative. No mobile changes, new authentication, mastery thresholds or quests.
- Legacy retries must retain their request digests; old snapshots remain readable. No destructive database recovery.
- Backend tests use an isolated temporary local PostgreSQL only. Android app and tests stay stopped.

## Task 1: Current-world snapshot and run continuation
- [x] Add regression tests for actual Android current-world payload, exact download, legacy idempotency and compact predecessors.
- [x] Observe expected failures, implement CURRENT_WORLD handling and response payloadKind without altering legacy digests.
- [x] Validate compact run continuation, malformed versions/generations/ancestor lists and legacy-to-current transition.
- [x] Run scoped tests, lint/type checks; report changed files and evidence.
Files: core/snapshots, infra/api/snapshots, snapshot tests. Avoid shared models unless essential: derive download kind from persisted JSON where possible.

## Task 2: Independent and partial-history analytics
- [x] Add regression tests for registered profile before any snapshot, analytics ahead of backup, restored historyStartSequence and retained facts/projections.
- [x] Observe expected failures; implement independent evidence intake with existing version/content checks, immutable facts and stable legacy digest.
- [x] Persist required range metadata using a data-preserving Alembic migration; avoid overwriting earlier evidence for equal end/different start.
- [x] Cover same-key replay/conflict, missing in-range facts, changed facts, invalid ranges, old migration data and restart boundaries.
- [x] Run scoped tests, lint/type checks; report changed files and evidence.
Files: core/analytics, infra/api/analytics, analytics storage/model sections, migration 0007, analytics tests. Snapshot code remains owned by task 1.

## Task 3: Integration and PR
- [x] Run fresh baseline before any production edits; agents may write tests while environment installs.
- [x] Add/update backend-facing contract documentation and real-client fixtures as appropriate.
- [x] Verify combined API scenarios, all tests, Ruff and ty. Review full diff independently, fix material issues.
- Delivery target: commit scoped changes, push codex/android-current-world-compatibility and create PR to main; attach PR to this task.

## Preflight
Task 1 produces accepted current-world storage; task 2 no longer consumes full snapshot history, so implementation files are independent. Shared PostgreSQL model edits belong only to task 2. Test DB migrations run serially with separate database names for concurrent scoped runs. Task 3 integrates both; no behavioral conflict with global constraints found.
