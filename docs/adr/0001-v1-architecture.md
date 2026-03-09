# ADR 0001: V1 platform topology

## Status

Accepted

## Decision

- Use a single monorepo with Next.js apps, FastAPI services, and Python workers.
- Use Postgres as the source of truth for domain state, events, and the outbox.
- Use Redis for cache, streams, and online feature state.
- Use Temporal for durable workflow orchestration.
- Use object storage for datasets, prompts, memory snapshots, and model artifacts.

## Consequences

- Agent cadence, retraining, and replay jobs get durable state and retries without bespoke schedulers.
- Event replay remains possible because all write-side mutations create canonical events.
- The initial stack is operationally heavier than a single-process app, but avoids a migration trap later.
