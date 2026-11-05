# Prento

Build a Linux laptop experiment comparing bounded push/backpressure and explicit receiver credits, independently of FIFO versus priority scheduling. C++20, real TCP producer → collector → controllably slow sink, Docker Compose, reproducible workloads, outcome accounting and tests. This is an application-layer experiment inspired by Homa; no Homa implementation, switch hardware or production capacity claims.

## Decisions

- One executable with collector, producer and sink commands. C++ standard library and POSIX sockets; no download required for a native Make build. CMake is also supplied for container builds.
- Full-batch admission with a byte reservation until sink completion. Four combinations: push/fifo, push/priority, credit/fifo, credit/priority. Priority favors critical traffic with a periodic bulk opportunity. No SRPT, packet preemption, unscheduled bytes, durable recovery or exactly-once claim in version one.
- Same persistent TCP connection for announce, optional grant, body, final acknowledgment. Collector reserves before reading body in both modes. Push can buffer in sender/kernel sockets; credits require explicit permission. Account for this difference in results.
- Bounded collector payload reservations and bounded producer metadata queues. Payloads are synthetic and allocated only at send time; report logical queued bytes separately from resident memory. Batch checksums detect corruption. No loss is silently called success.
- Producers generate on an intended schedule independent of completions, with bounded local queues. Every generated item gets exactly one CSV terminal outcome (completed, failed/unknown, producer_drop). A failed/unknown result can have reached the sink; never claim zero duplicates or exactly-once.
- Sink serializes processing so configured service rate is a global bottleneck. Slowdown/outage intervals are tied to sink start and recorded. Completion means sink processing ACK, not durable storage.
- Fixed CPU/memory budgets, per-class latency including producer waiting, offered/admitted/completed rates, data loss and both endpoint RSS. Fixed workloads/seeds; real execution timings are not deterministic.
- Native runs are explicitly unrestricted by this program: record hardware and competing load. Container runs can apply a fixed budget. Sink slowdown/outage scenarios act at batch service entry: an already processing batch is not interrupted, and a slowdown multiplier applies to that full batch. This is not a network partition or durable-backend failure model.
- Priority offers bulk a turn after the critical quota only among requests that fit currently available reservation space. It does not guarantee a finite delay for oversized relative-to-free-space bulk work. Each producer exposes only its next batch, so a critical batch can also wait behind earlier local bulk work.
- HTTP health/metrics endpoint, bounded connections, socket timeouts and orderly SIGTERM cleanup. Lab ports are unauthenticated: bind to loopback locally; TLS/authentication are future deployment work.

## Deliverables and limits

README with measured results, architecture and limitations; source/tests; Makefile/CMake; non-root multi-stage container/Compose; benchmark and report commands producing CSV/JSON/standalone SVG; CI; actual agent workflow record. Kubernetes manifests demonstrate deployment only and are secondary to working native/Compose verification.

Keep changes isolated to this project. Publishing or creating an external repository requires a separate user instruction.

## QA update

Sink sleeps are bounded by the remaining requested duration, with deterministic injected-clock regression checks; OS wake-up precision is not guaranteed. TCP integration with a controlled backend proves admission ordering and full-budget grant withholding. Reporting splits completed-message latency into pre-send and post-send intervals, validates matched configuration and inputs, and retains completion changes and observed maxima. Multi-seed trials keep the four modes unchanged; no producer-side priority is introduced. Historical raw evidence remains separate from corrected-timer data.
