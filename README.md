# Prento

**Pronunciation:** PREN-to. **Intended association:** prompt delivery and operational readiness.

A reproducible laptop experiment comparing **bounded TCP push/backpressure** and **receiver-issued credits**, independently of FIFO versus priority scheduling.

This project investigates a question: *does coordinated admission across producers help beyond priority-aware backpressure when a telemetry sink slows down?* It is an application-layer experiment inspired by Homa's receiver control. It is not an implementation of Homa and does not establish a novel transport algorithm.

**Observed result:** in 144 corrected-timer container trials over three workload seeds, priority-aware push reduced mean critical end-to-end latency about **10% under bursts** and **13% with a slow sink**, versus push/FIFO. With priority enabled, **98.7% of remaining critical latency under bursts and 98.1% with a slow sink occurs before sending**. Credits added no consistent benefit beyond priority-aware push. All **79,236 generated messages completed** after drain, with no drops or unknown outcomes. Individual critical samples remain small; these results do not establish a tail SLO or production capacity. See [interpretation and trade-offs](results/2026-11-04-qa/INTERPRETATION.md), [full measured report](results/2026-11-04-qa/REPORT.md) and [QA verification](qa/VERIFICATION.md). The [initial 48-trial evidence](results/2026-11-04-container/FINDINGS.md) is preserved separately; its older timer/service model is not directly comparable.

## QA handoff

The QA ZIP includes source, tests, Docker/Compose/Kubernetes configuration, complete raw results, latency charts, verification logs and reproduction instructions. Start at [qa/README.md](qa/README.md). On a fresh extraction run `python3 scripts/verify_bundle.py . --strict` and `python3 qa/check_evidence.py`. Rebuild the archive with `make qa-bundle`; its adjacent SHA-256 file verifies the ZIP. Compiled binaries and Git metadata are excluded.

## Run the three-service demo

Requirements: Docker Desktop with Linux containers (WSL2 on Windows), or Docker Engine and Compose on Linux. The build image contains the compiler and CMake.

```sh
docker compose build
docker compose up -d sink collector
docker compose run --rm producer
docker compose logs collector
```

Retrieve the raw outcomes from the named results volume with:

```sh
docker compose run --rm --entrypoint cat producer /results/outcomes.csv
docker compose down
```

Collector metrics and health: [http://localhost:19090/metrics](http://localhost:19090/metrics), `/readyz`, `/livez`. Health means the process can accept connections; it does not establish sink durability or upstream health. Service containers run as non-root with dropped capabilities, read-only root filesystems and fixed resource limits. Only the metrics port is published, on loopback.

Choose the mode before starting the stack:

```sh
ADMISSION=push POLICY=fifo docker compose up -d --force-recreate sink collector
ADMISSION=push POLICY=fifo docker compose run --rm producer
```

Keep producer and collector admission settings identical. On PowerShell use `$env:ADMISSION="push"; $env:POLICY="fifo"` before the Compose commands. Start fresh services for a fresh slowdown schedule.

## One-command experiment

Run all four policies over steady, burst, slow-sink and outage-like-pause scenarios inside one fixed-budget benchmark container:

```sh
docker compose --profile bench run --build --rm benchmark
```

The benchmark runner launches separate producer, collector and sink processes over real loopback TCP within that container. It uses the same program as the demo, but is not a multi-container network-capacity test. Results are retained in the `bench-results` named volume. A nonempty output directory is protected from overwriting. For another run choose a new output name:

```sh
docker compose --profile bench run --rm benchmark --output /results/run-2
docker compose --profile bench run --rm --entrypoint cat benchmark /results/run/REPORT.md
```

Each run includes `outcomes.csv`, command/config JSON, process logs, sampled producer/collector/sink RSS and CPU time, and final collector metrics. CPU sampling can miss work after the last sample, especially very short runs. The suite produces `REPORT.md`, `FINDINGS.md`, per-run and aggregate JSON, matched-message comparisons and `latency-breakdown.svg`.

## Native Linux / WSL

Only GCC supporting C++20, Make and Python 3 are needed. There are no downloaded C++ libraries or Python packages.

```sh
make test
make sanitize
make bench
```

Alternatively, `cmake -S . -B build-cmake && cmake --build build-cmake && ctest --test-dir build-cmake` builds the binary and core tests. Full process tests use `FANIN_BINARY=/absolute/path/to/fanin python3 -m unittest discover -s tests -p 'test_*.py' -v`.

Change the workload explicitly:

```sh
python3 scripts/bench.py --output results/my-run --seeds 7,42,2026 --repeats 3 --duration-ms 10000 --critical-fraction 0.2 --producers 32
python3 scripts/report.py results/my-run
```

Native runs do **not** apply CPU or memory isolation. Record competing load; use a container budget or dedicated hosts for stronger comparisons. `/proc` sampling is Linux-specific and sampled RSS can miss brief peaks.

## Architecture and comparison

```text
fixed-schedule generator -> bounded producer queues -> TCP collector -> serialized slow sink
                                                     admission + ready-work scheduling
```

| Mode | Admission | Scheduling |
|---|---|---|
| push/fifo | Read payload only when reservation space is available | FIFO among fitting requests |
| push/priority | Same bounded read policy | Critical preference with periodic bulk opportunities |
| credit/fifo | Announce metadata, wait for explicit full-batch grant | FIFO among fitting requests |
| credit/priority | Same explicit grants | Critical preference with periodic bulk opportunities |

Compare push/FIFO with push/priority for priority's effect; push/FIFO with credit/FIFO for credits; and push/priority with credit/priority for credits beyond a priority-aware baseline. All modes use identical payloads, checksums, sink processing and source scheduling.

The collector reserves the full payload size before reading it and releases its reservation after sink completion/failure. In push mode payloads may already occupy producer and kernel socket buffers. In credit mode producers wait for the explicit permission. Both inherit TCP flow control. Up to `max-clients` concurrent sessions are accepted; completed thread handles are reaped.

Each producer has one outstanding batch per connection. Only that next batch is announced; later critical work can wait behind earlier producer-local work. No packet SRPT, true preemption or unscheduled fast path is implemented. The quota offers bulk a turn among fitting work, rather than guaranteeing bounded bulk delay when its entire batch cannot fit.

## Workload and measurements

Defaults: 16 producer connections, 100 generated batches/s globally, 5% critical messages by count, 256-byte critical messages and 32-KiB bulk batches. These are synthetic settings, not assertions about Splunk traffic. Traffic class and size can be configured independently. A fixed seed preserves message classes and assignment; OS scheduling and timings vary. Suite order is shuffled deterministically to reduce systematic order bias.

- **Latency:** intended generation time through sink processing ACK, including producer waiting. Timestamp decomposition separates pre-send from post-send time; neither isolates collector queueing. Report means, observed maxima and counts. Empirical p50/p99/p99.9 remain inspectable in JSON.
- **Outcomes:** exactly one CSV row per generated logical ID: `completed`, `producer_drop`, or `failed_unknown`. A failed/unknown delivery may have reached the sink, so never call it known loss or retry it as exactly-once.
- **Throughput:** offered bytes and bytes completed during the offered-load window; report drain time separately. Final admitted batch/byte counters are exposed for external rate sampling.
- **Memory:** collector reserved bytes and sampled RSS for all three processes. Reservation cap is not a process-RSS or total-system-memory cap. Generator queues contain metadata; payloads are synthesized at send time. Report logical queued bytes separately.
- **Sink:** one shared service mutex serializes all sessions. Slowdown multipliers and outage-like pauses are evaluated at batch service entry. Work already processing is not interrupted, and a chosen multiplier applies for the whole batch. These scenarios are not actual packet loss, network partitions or durable-backend crashes.

Short default runs produce few critical samples. Their p99 is exploratory and near the observed maximum; longer runs, multiple workload seeds and independent-host experiments are necessary before claiming tail improvement or capacity. Never extrapolate laptop loopback results to a physical fabric. Read [DESIGN.md](DESIGN.md) and the measured report together.

## Wire protocol and completion semantics

A 32-byte network-order header carries magic/version, type, class, admission mode, ID, payload length, FNV-1a checksum and intended timestamp. Types are ANNOUNCE, GRANT, ACK and REJECT. The sender announces, optionally waits for a grant, sends exactly the declared payload and waits for the final processing acknowledgment. Full-batch grants add one 32-byte application message; report actual latency instead of assuming a fixed percentage penalty.

This is a custom lab protocol, **not OTLP or gNMI**. Fixed-size headers, bounded batch lengths, checksums and socket deadlines reject malformed data. FNV-1a is a corruption check, not authentication. Ports are unauthenticated; local runs bind loopback. Distributed deployment needs transport authentication, policy enforcement and a supported adapter. ACK means completion of simulated sink processing, not fsync, Kafka replication or exactly-once delivery.

The source does not retry failed batches. Receiver credits and state are local to one collector. Kubernetes connections stay pinned to their selected collector; adding pods does not redistribute existing TCP streams.

## Kubernetes example

`deploy/kubernetes.yaml` supplies two collectors, one bottleneck sink, Services and producer Jobs. Replace image tags with your registry digest (or explicitly load the image into a local cluster), then apply it in an isolated namespace. Job results are on ephemeral pod storage; copy them before deleting pods. This example has no HPA, custom metrics adapter or durability and is **not evidence of multi-node scaling**. Adding collectors cannot scale past the shared sink's capacity.

## Future work

Streaming/chunk grants and SRPT, producer-local priority, authenticated adapters for OTLP/gNMI, OTel Collector interoperability baseline, durable acknowledgment/replay, and tests on independent physical hosts. Each is a separate experiment; none is claimed complete here.

Source: [sapenov/prento](https://github.com/sapenov/prento).

Engineering record and validation: [docs/ENGINEERING.md](docs/ENGINEERING.md). See the [producer-latency effort estimate](docs/PRODUCER_LATENCY.md), [QA review decisions](qa/REVIEW.md) and [MIT license](LICENSE).

## References

- [Homa protocol synopsis](https://github.com/PlatformLab/HomaModule/blob/main/protocol.md): receiver grants, scheduling and where the inspiration comes from.
- [gRPC flow control](https://grpc.io/docs/guides/flow-control/): existing receiver/transport controls that motivate a strong baseline.
- [OpenTelemetry Collector benchmarks](https://opentelemetry.io/docs/collector/benchmarks/): future interoperability comparison; not implemented in this custom-protocol lab.
- [wrk2 measurement discussion](https://github.com/giltene/wrk2): intended-send-time latency and coordinated omission. This lab does not depend on wrk2.
