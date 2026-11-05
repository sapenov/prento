# Verification record

This is the preserved **initial-version** record. Its sink timer had a one-millisecond sleep floor. The corrected implementation, additional tests and multi-seed evidence are documented in [the QA verification record](../qa/VERIFICATION.md). Do not combine results across these service models.

Observed in this task on November 4, 2026, America/New_York. No remote publication occurred.

| Check | Result |
|---|---|
| Native GCC 13.3 release build, warnings as errors | Passed |
| `make test` | 14 core assertions plus 11 Python tests passed |
| `make sanitize` | Same core and real-process suite passed under AddressSanitizer and UndefinedBehaviorSanitizer |
| Runtime Docker build | Passed; CMake build and CTest core suite passed in build stage |
| Benchmark Docker build | Passed |
| `docker compose config --quiet` | Passed |
| Three-service Compose demo | 300 generated, 300 completed, zero producer drops or unknown outcomes |
| Fixed-budget benchmark container | Exit 0, 48/48 trials completed; no OOM kill |
| Outcome accounting | 15,852 generated = 15,852 completed across trials |
| Reservation invariant | All 48 final counters show peak ≤262,144 bytes and current reservation 0 |
| Independent read-only code review | Important lifecycle and packaging findings corrected; focused recheck found no remaining Critical/Important issues |
| Kubernetes example | Supplied and reviewed statically; not deployed to a cluster |
| ThreadSanitizer | Not run; ASan/UBSan do not prove absence of data races |

Final native command log: `make test` reported 11 Python tests in 9.177 seconds, all OK, plus 14 core checks. Final sanitizer command log reported 11 Python tests in 10.094 seconds, all OK, plus the sanitized core checks. Sanitizers use separate binaries; release benchmarks do not use instrumented executables.

## Container evidence

Benchmark image: `sha256:b0599350e79dd0800bd1e7e15fd624d0d59129a00f2a096e134a50277061669a` (`linux/amd64`). Application binary SHA-256: `bc87d775b8918b8336514a614e20b5066e2b51675699c795c6fbe94556795660`.

Measured limits: `NanoCpus=4000000000`, `Memory=1073741824`; inside the container `cpu.max=400000 100000` and `memory.max=1073741824`. Host reports Intel Core i9-10885H, 16 logical CPUs, Linux/WSL2. This is a shared laptop, not an isolated physical benchmark cluster.

The benchmark runner started separate real-TCP producer, collector and sink processes inside one fixed-budget container. The separate three-container Compose wiring was also verified. Neither establishes physical-network or multi-node Kubernetes scale.

## Evidence locations

- [Findings](../results/2026-11-04-container/FINDINGS.md)
- [Every per-run p99 and outcome count](../results/2026-11-04-container/REPORT.md)
- [Machine and container environment](../results/2026-11-04-container/environment.json)
- [Structured summaries](../results/2026-11-04-container/summary.json)
- Per-run subdirectories hold raw CSV, logs, exact commands and collector counters.

Limitations: completion is simulated sink processing, not durability; slow/outage-like intervals act at batch entry; source queues are synthetic metadata; bulk fairness is among fitting requests; p99 estimates have small critical sample sizes; no external OTel baseline, automatic alert detection, Kafka, actual Homa, switch installation or cloud deployment is claimed.
