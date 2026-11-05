# Engineering notes

Prento uses dependency-free C++20 and POSIX TCP sockets to compare receiver credits with bounded push, independently of priority scheduling. Tests exercise the actual producer, collector and sink.

## Implementation and verification

| Area | Behavior and evidence |
|---|---|
| Idle connections | Persistent sessions poll while idle; frame deadlines apply once bytes start arriving. Low-rate producer tests cover connection reuse. |
| Input validation | Command-specific option allowlists reject unknown settings. Producer options are validated before workers start. |
| Shutdown | Scheduled waits check the atomic stop flag at short intervals for prompt SIGTERM handling. |
| Session lifecycle | Completed connection threads are reaped during operation; live peer caps remain enforced. |
| Containers | Result-directory creation is idempotent. The Kubernetes example supplies writable-volume group permissions. |
| Sink timing | Sleep requests are bounded by the remaining duration. Injected-clock tests cover short requests, final remainders, zero duration and cancellation. Actual wake-up precision depends on the OS. |
| Measurement validation | Paired comparisons require matching logical workloads, sink/load/buffer/queue/timeout settings and recorded executable identities. Timestamp intervals include all pre-send and post-send work. |
| Scheduling | Controlled TCP tests independently verify admission priority and service order among ready payloads. Separate mutations verify sensitivity to both selectors and premature grants. |
| Failure diagnostics | NetworkTest failures retain commands, logs, outcomes, producer output and timeout information. A filesystem fixture verifies retention; CI uploads the artifacts. |
| Packaging | Metadata distinguishes source payloads, checked payloads and archive entries. Reserved names are rejected. Strict checksum verification detects extra files in a fresh extraction. |

Git attributes preserve source and experiment bytes across checkout platforms. Whitespace checks exclude recorded formatting in raw results and console logs. Public logs normalize local workspace prefixes without changing outcomes or timing values.

## Execution environment

The [recorded CI run](https://github.com/sapenov/prento/actions/runs/41965080263) passed native tests, sanitizers and the runtime Docker build. On the measured WSL host, TSan requires per-process `setarch -R` to avoid a startup memory-mapping failure; no host-wide setting is changed. [QA verification](../qa/VERIFICATION.md) identifies the commands, logs and measured-image provenance.

The suite contains 18 core checks and 26 Python tests. The three-service Compose demo completed 300/300 messages. The main performance matrix completed 79,236/79,236 messages across 144 trials. Application fingerprints match the measured image.

## Limits and further work

The experiment does not establish a production tail SLO, durable completion, exactly-once delivery or multi-node scale. Sink pauses act at batch entry, batches are non-preemptive and producer-local FIFO blocking remains. Kubernetes deployment, actual Homa, telemetry adapters and producer-priority optimizations have not been measured here.

See the [coverage notes](../qa/REVIEW.md), [benchmark findings](../results/2026-11-04-qa/INTERPRETATION.md) and [producer-latency options](PRODUCER_LATENCY.md). A [48-trial reference dataset](VERIFICATION.md) has different sink-timing and load settings and must be considered separately.
