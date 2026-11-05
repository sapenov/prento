# Engineering and verification record

Prento uses a dependency-free C++20 TCP protocol to compare receiver credits with bounded push, independently of priority scheduling. Its tests exercise the actual producer, collector and sink. Automated and AI-assisted code review complement those tests; they do not constitute a human QA sign-off.

## Defects found and corrected

- **Idle connections:** persistent sessions previously timed out before their next batch. Collector and sink now poll idle sessions, applying a frame deadline once bytes start arriving. Low-rate producer tests cover reuse.
- **Input validation:** command-specific option allowlists reject unknown settings, and producer options are validated before workers start.
- **Shutdown:** scheduled producer waits check the atomic stop flag at short intervals, allowing prompt SIGTERM handling.
- **Session lifecycle:** completed connection threads are reaped during operation while live peer caps remain enforced.
- **Container wiring:** result-directory creation is idempotent, and the Kubernetes example supplies writable-volume group permissions.
- **Sink timing:** remaining-time sleeps replace the artificial one-millisecond minimum. Injected-clock tests cover submillisecond requests, final remainders, zero duration and cancellation. OS wake-up precision remains outside the model's control.
- **Measurement validation:** paired comparisons reject different logical workloads, sink/load/buffer/queue/timeout settings and executable identities. Pre-send and post-send intervals are derived from timestamps; neither is labeled isolated collector queueing.
- **Scheduling coverage:** controlled TCP integration independently verifies admission priority and service ordering among already admitted payloads. Separate mutations disable admission priority, disable service priority and issue a grant before reservation; each is rejected by its relevant test.
- **Failure diagnostics:** NetworkTest cases retain commands, logs, outcomes, producer output and timeout information on failure. A filesystem fixture verifies retention, and CI uploads the artifacts. One reported overload-test flake remains unconfirmed because its original error was not captured.
- **Archive integrity:** metadata distinguishes source payloads, checked payloads and archive entries. Reserved metadata names are rejected; optional strict verification detects unlisted files before a fresh extraction is built.

## Execution issues retained as evidence

Plain ThreadSanitizer startup failed on the WSL host with an unexpected memory mapping. Per-process `setarch -R` allowed execution; both the initial failure and successful runs are retained. No host-wide address-randomization setting changed.

A report-regeneration attempt started before Docker copying finished and rejected an incomplete group. An archive check started before the ZIP writer finished and found no archive. Both checks passed once their input-producing commands had completed; the failed report attempt remains in the logs.

The initial GitHub Actions configuration used a runner-only context at job level and failed validation before creating jobs. A relative diagnostic directory corrected it. The [subsequent CI run](https://github.com/sapenov/prento/actions/runs/41965080263) passed native tests, sanitizers and the runtime Docker build.

Git attributes preserve source and experiment bytes across checkout platforms. Whitespace checks exclude original formatting in raw results and console logs. Public logs normalize local workspace prefixes without altering recorded outcomes or timing values.

## Evidence and limits

The current suite has 18 core checks and 26 Python tests. Native, ASan/UBSan, TSan and Docker test runs passed; Compose completed 300/300 messages. The 144-trial performance matrix completed 79,236/79,236 messages over three workload seeds. Application fingerprints still match the measured image.

See [QA verification](../qa/VERIFICATION.md), [review findings](../qa/REVIEW.md), [measured interpretation](../results/2026-11-04-qa/INTERPRETATION.md) and [producer-latency options](PRODUCER_LATENCY.md). The older [initial-version record](VERIFICATION.md) uses a different sink timer and remains separate.

The experiment does not establish protocol novelty, a production tail SLO, durable completion, exactly-once delivery or multi-node scale. Sink pauses act at batch entry, batches are non-preemptive, and producer-local FIFO blocking remains. Kubernetes deployment, actual Homa, telemetry adapters and producer-priority optimizations have not been measured here.
