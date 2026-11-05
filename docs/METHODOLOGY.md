# Methodology and protocol

Prento compares admission and scheduling independently. Read the [benchmark findings](../results/2026-11-04-qa/INTERPRETATION.md) alongside these definitions.

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

Defaults: 16 producer connections, 100 generated batches/s globally, 5% critical messages by count, 256-byte critical messages and 32-KiB bulk batches. These synthetic settings do not represent a particular production workload. Traffic class and size can be configured independently. A fixed seed preserves message classes and assignment; OS scheduling and timings vary. Suite order is shuffled deterministically to reduce systematic order bias.

- **Latency:** intended generation time through sink processing ACK, including producer waiting. Timestamp decomposition separates pre-send from post-send time; neither isolates collector queueing. Report means, observed maxima and counts. Empirical p50/p99/p99.9 remain inspectable in JSON.
- **Outcomes:** exactly one CSV row per generated logical ID: `completed`, `producer_drop`, or `failed_unknown`. A failed/unknown delivery may have reached the sink, so never call it known loss or retry it as exactly-once.
- **Throughput:** offered bytes and bytes completed during the offered-load window; report drain time separately. Final admitted batch/byte counters are exposed for external rate sampling.
- **Memory:** collector reserved bytes and sampled RSS for all three processes. Reservation cap is not a process-RSS or total-system-memory cap. Generator queues contain metadata; payloads are synthesized at send time. Report logical queued bytes separately.
- **Sink:** one shared service mutex serializes all sessions. Slowdown multipliers and outage-like pauses are evaluated at batch service entry. Work already processing is not interrupted, and a chosen multiplier applies for the whole batch. These scenarios are not actual packet loss, network partitions or durable-backend crashes.

Short default runs produce few critical samples. Their p99 is exploratory and near the observed maximum; longer runs, multiple workload seeds and independent-host experiments are necessary before claiming tail improvement or capacity. Never extrapolate laptop loopback results to a physical fabric. Read [architecture decisions](../DESIGN.md) and the measured report together.

## Wire protocol and completion semantics

A 32-byte network-order header carries magic/version, type, class, admission mode, ID, payload length, FNV-1a checksum and intended timestamp. Types are ANNOUNCE, GRANT, ACK and REJECT. The sender announces, optionally waits for a grant, sends exactly the declared payload and waits for the final processing acknowledgment. Full-batch grants add one 32-byte application message; report actual latency instead of assuming a fixed percentage penalty.

This is a custom lab protocol, **not OTLP or gNMI**. Fixed-size headers, bounded batch lengths, checksums and socket deadlines reject malformed data. FNV-1a is a corruption check, not authentication. Ports are unauthenticated; local runs bind loopback. Distributed deployment needs transport authentication, policy enforcement and a supported adapter. ACK means completion of simulated sink processing, not fsync, Kafka replication or exactly-once delivery.

The source does not retry failed batches. Receiver credits and state are local to one collector. Kubernetes connections stay pinned to their selected collector; adding pods does not redistribute existing TCP streams.

## References

- [Homa protocol synopsis](https://github.com/PlatformLab/HomaModule/blob/main/protocol.md): receiver grants, scheduling and where the inspiration comes from.
- [gRPC flow control](https://grpc.io/docs/guides/flow-control/): existing receiver/transport controls that motivate a strong baseline.
- [OpenTelemetry Collector benchmarks](https://opentelemetry.io/docs/collector/benchmarks/): future interoperability comparison; not implemented in this custom-protocol lab.
- [wrk2 measurement discussion](https://github.com/giltene/wrk2): intended-send-time latency and coordinated omission. This lab does not depend on wrk2.
