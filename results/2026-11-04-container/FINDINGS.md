# Observed result and limitations

48 trials: four modes × four scenarios × three repeats. The same seed repeats message classes and sizes; timings vary. Each offered-load window is three seconds. The container was capped at four CPUs and 1 GiB RAM on a shared WSL2 laptop.

| Scenario | Push/FIFO critical p99 ms | Push/priority critical p99 ms | Credit/FIFO critical p99 ms | Credit/priority critical p99 ms | Critical samples per run |
|---|---:|---:|---:|---:|---:|
| steady | 2.08 | 1.94 | 2.30 | 2.13 | 13 |
| burst | 1082.73 | 1030.57 | 1108.20 | 1007.89 | 18 |
| slow | 772.43 | 685.95 | 811.59 | 693.72 | 13 |
| outage | 897.62 | 898.05 | 897.67 | 898.14 | 13 |

Numbers above are the median of three per-run p99 values, not a pooled p99. Short critical samples make these exploratory near-maximum observations. No statistical significance claim is made.

## Findings

- Priority-aware push reduced the median critical p99 about 5% during the burst and 11% with the slow sink relative to push/FIFO in this workload.
- Receiver credits did not consistently improve on priority-aware push. They were slightly better in one scenario and worse in others. The extra protocol is not justified by a general performance claim from these runs.
- No material priority benefit appeared during the outage-like pause: the blocked sink dominates completion delay.
- Every run completed all generated messages after drain: 15,852 generated and completed in aggregate, zero producer drops, zero delivery-unknown outcomes. This is a finite-run observation, not a delivery guarantee.
- Collector reservation peaks stayed within the configured 262,144-byte budget and returned to zero in all 48 runs. This is a payload-reservation bound, not total process or kernel memory.

## Why the improvement is limited

The implementation intentionally uses whole batches and one in-flight batch per producer connection. Critical work can wait behind earlier producer-local bulk work before its metadata is announced. Processing is non-preemptive. Credits coordinate only the next announced batch, and both push and credit already enforce the same receiver byte budget. These constraints narrow the possible benefit.

## What to say in an interview

> I built a C++ telemetry fan-in experiment with four controlled baselines. Priority improved selected overload cases modestly, but explicit credits did not consistently beat priority-aware push. The result favored keeping the simpler mechanism for this workload. I documented source-side head-of-line blocking, finite buffering, ambiguous acknowledgments and the limits of laptop tail measurements.

A subsequent experiment could isolate producer-local priority or chunk-level preemption. Those are not implemented or measured here.

Raw per-run outcomes, configuration, counters and the machine/container environment accompany this report. See [REPORT.md](REPORT.md) and [summary.json](summary.json).
