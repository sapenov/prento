# Effort to reduce producer-side latency

This is an engineering estimate, not an implemented optimization or predicted benchmark result. Effort means focused hours for an experienced C++ engineer, including verification; coding-agent elapsed time can differ. The existing 144-trial measurements remain unchanged.

## What the current measurements establish

For push/priority, critical means are 729.86 ms pre-send + 9.79 ms post-send in bursts, and 708.10 + 14.06 ms with a slow sink. Pre-send accounts for 98.7% and 98.1% of the remaining total. Source: [raw-backed interpretation](../results/2026-11-04-qa/INTERPRETATION.md).

The producer pops a FIFO item, prepares its body, sends its announcement and waits for a final processing ACK before taking another item. Thus later critical work cannot bypass either queued bulk work or an outstanding bulk operation on that worker. Only the next batch is visible to the collector. Pre-send also contains intended-generation lateness, body preparation and connection setup; current timestamps do not isolate those components. The 98% share is not proof that every pre-send millisecond is removable queueing.

## Staged options

| Work | Implementation and evidence | Focused effort | Expected limit |
|---|---|---:|---|
| Finer source timestamps | Record actual generation, dequeue and preparation/connection intervals; validate timestamp accounting and compare class distributions | 2–4 hours | Diagnoses the delay; does not itself reduce it |
| Priority within each producer's pending queue | Critical preference with quota/aging, unchanged total queue bound; deterministic producer-order tests, failure accounting, three-seed comparison and report | 8–16 hours, roughly 1–2 days | Can bypass queued bulk; still waits for a bulk batch already in flight |
| Separate critical and bulk sending lanes | A separate connection/worker can announce critical work while bulk waits; preserve a shared queue budget and compare equal connection/resource counts | 16–32 hours, roughly 2–4 days | More concurrency, sockets and fairness policy; cannot bypass active backend work or an actual pause |
| Multiplexed/chunked transfer | Explicit framing/interleaving, per-message state, bounded chunks/credits, cancellation and failure tests, new fair baselines | 1–2 weeks | Largest protocol change and validation burden; still cannot create backend capacity |

The lane estimate is an alternative next step, not an additive promise that all work finishes in four days. Containerized benchmark runs, interpretation and regression checks are included in the ranges. Independent-host or production integration work is additional.

Recommendation: budget 1–2 days for finer measurements and pending-queue priority as the first controlled experiment, allowing another half-day if instrumentation or validation uncovers an unexpected source of delay. Defer extra lanes until the residual in-flight wait is measured. Reuse the current collector admission/service policies.

## How much could it improve?

The following is sensitivity arithmetic only, computed from unrounded aggregate means (the displayed inputs above are rounded). It assumes the chosen fraction of pre-send time disappears while post-send time stays fixed. Real scheduling can move the queue downstream and affect other traffic, so these values are not forecasts.

| Hypothetical pre-send reduction | Burst total mean | Burst total reduction | Slow-sink total mean | Slow-sink total reduction |
|---|---:|---:|---:|---:|
| 25% | 557.19 ms | 24.67% | 545.13 ms | 24.51% |
| 50% | 374.72 ms | 49.34% | 368.11 ms | 49.03% |
| 90% | 82.78 ms | 88.81% | 84.87 ms | 88.25% |

There is no supported percentage estimate for pending-queue priority until that variant is measured. Its likely opportunity is bypassing queued bulk. Full-batch non-preemption and backend pauses remain lower bounds on progress. The 9.79/14.06 ms post-send means are measured averages, not guaranteed floors for every future variant.

## Acceptance and fair comparison

Measure intended generation through final ACK, not merely the time until sending. Keep logical input IDs, schedules, classes, bytes, offered load, queue byte/item budgets, collector capacity and machine limits fixed. A lane comparison must control total connections/workers so added parallelism is not attributed entirely to scheduling. Record any necessary baseline change explicitly.

Report critical pre/post/total means, observed maxima, matched faster/slower counts, completion/drop/unknown counts, bulk delay, memory and CPU. Run the existing steady/burst/slow/pause scenarios over at least the current three seeds; a full current-length 144-trial container matrix takes roughly 15 minutes plus analysis on the measured laptop. Add critical-share and saturation sweeps as a separate validation stage. Longer runs are necessary for credible tail estimates.

Tests must show that pending critical work overtakes queued bulk, an in-flight bulk batch remains non-preemptive, bulk still progresses, and overload/failure/shutdown preserve one terminal outcome per logical message. A lower pre-send number with unchanged or worse end-to-end latency is not a successful optimization.
