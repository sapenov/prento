# Reference dataset: 48 trials

This dataset uses four scenarios × four modes × three timing repeats, workload seed 42, three-second offered-load windows and a one-millisecond minimum sink sleep. It was measured on November 4, 2026 (America/New_York).

The [main 144-trial benchmark](../qa/VERIFICATION.md) uses three seeds, five-second windows and sleeps bounded by the remaining requested duration. These service/load configurations differ; comparing their results cannot isolate a timer-related speedup. Use the main benchmark for the README findings.

## Recorded results

| Check | Result |
|---|---|
| Benchmark completion | 48/48 trials; container exit 0 without OOM |
| Outcome accounting | 15,852 generated = 15,852 completed; no drops or unknowns |
| Collector reservations | Every peak ≤262,144 bytes; final reservation zero |
| Critical samples | 13–18 per run; p99 values are exploratory near-maximum observations |

The [findings](../results/2026-11-04-container/FINDINGS.md) summarize the median of three per-run p99 values, rather than a pooled percentile. The [complete report](../results/2026-11-04-container/REPORT.md) lists all trials. Each trial directory includes raw outcomes, exact commands and collector counters.

## Configuration and identity

Separate producer, collector and sink processes communicate over loopback inside a container limited to four CPUs and 1 GiB. The shared WSL2 laptop reports Intel Core i9-10885H and 16 logical CPUs. This setup does not establish physical-network capacity or Kubernetes scale.

Benchmark image: `sha256:b0599350e79dd0800bd1e7e15fd624d0d59129a00f2a096e134a50277061669a` (`linux/amd64`).

Executable SHA-256: `bc87d775b8918b8336514a614e20b5066e2b51675699c795c6fbe94556795660`.

See the [environment](../results/2026-11-04-container/environment.json) and [structured summaries](../results/2026-11-04-container/summary.json). Completion means simulated sink processing, not durable storage. Batches are non-preemptive, and slowdown/pause settings apply at service entry.
