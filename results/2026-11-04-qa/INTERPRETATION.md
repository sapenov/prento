# What the corrected experiment shows

The simpler priority-aware push baseline is the strongest default in this measured workload. Receiver credits did not show a consistent additional end-to-end advantage. These are descriptive laptop results, not statistical significance or production recommendations.

The matrix contains 144 trials: four scenarios × four modes × three workload seeds (7, 42, 2026) × three timing repeats. Each trial offers load for five seconds, then drains. All 79,236 generated logical messages completed, with no producer drops or delivery-unknown outcomes. All collector reservation peaks stayed within 262,144 bytes and final reservations/queues returned to zero. See [the full report](REPORT.md), [environment](environment.json) and [QA verification](../../qa/VERIFICATION.md).

## Priority's benefit and its limits

Compare push/FIFO against push/priority, keeping admission unchanged. Values below are equally weighted means of the nine runs in each cell. Positive reduction means lower latency.

| Scenario | Critical total, FIFO → priority | Total reduction | Per-seed reduction range | Post-send, FIFO → priority | Bulk mean change |
|---|---:|---:|---:|---:|---:|
| Burst | 825.51 → 739.65 ms | 10.40% | 6.70% to 15.87% | 92.38 → 9.79 ms | +0.95% |
| Slow sink | 833.05 → 722.15 ms | 13.31% | 7.70% to 19.43% | 116.17 → 14.06 ms | −1.23% |
| Outage-like pause | 959.81 → 911.95 ms | 4.99% | −1.02% to 9.26% | 127.63 → 47.90 ms | +4.05% |

The burst and slow-sink post-send means fall about 89% and 88%, but **end-to-end reductions are only 10% and 13%**. Most remaining time is pre-send: the one-outstanding-batch producer FIFO prevents later critical work from even being announced. Post-send includes transfer, admission, ready-work waiting, sink work and acknowledgment; its reduction is not proof of isolated collector-queue improvement.

Better mean latency does not imply better tails or every message becoming faster. In the burst scenario the largest observed critical latency rises from 1,622.30 to 1,649.06 ms. Only 264 of 342 matched critical messages are faster; the rest are slower. The report retains all matched messages and shows bulk costs rather than selecting a favorable subset.

## Credits beyond priority-aware push

Compare push/priority against credit/priority. Critical mean end-to-end latency is 5.39% higher with credits in bursts and 3.45% higher with a slow sink. It is 2.09% lower during the outage-like pause, with a per-seed range from a 0.40% regression to a 6.99% reduction. At steady load it rises from 0.95 to 1.28 ms. This supports reporting **no consistent incremental win**, not claiming that receiver credits can never help.

The steady-state priority comparison is also noisy: about 0.10 ms lower mean in aggregate, with a per-seed range that crosses zero. Its percentage is not a useful headline. The finite scenario changes and service-entry timing can also make bulk means fluctuate in either direction; scheduling does not create backend capacity.

## What QA should challenge

Each individual trial has only 22–45 completed critical messages. Nearest-rank p99 therefore selects the observed maximum; p99 and p99.9 remain inspectable in JSON but cannot establish a tail SLO. Per-seed ranges are descriptive ranges over three seeds, not confidence intervals. Matched logical inputs do not remove OS scheduling variability or shared-host interference.

All processes communicate over loopback inside one container capped at four CPUs and 1 GiB; the host is a shared WSL laptop. The sink is a serialized, non-preemptive service simulator. Completion is not durable storage. Batch-entry pauses are not actual backend crashes or network partitions. Raw timestamp-derived breakdowns, configuration validation, image/binary provenance and logs are included so QA can inspect these limits.

The preserved initial-version runs used a one-millisecond sleep floor and shorter load windows. They are historical evidence, not a controlled before/after timer-speed benchmark. No percentage improvement from fixing the timer is claimed.

A sensible next experiment would isolate producer-local priority or chunked admission, one variable at a time. Neither is implemented here. For the interview, the defensible result is the comparison and diagnosis: collector priority helps, upstream blocking limits the user-visible benefit, and the extra credit mechanism needs a stronger use case.
