# QA handoff — corrected timer and latency decomposition

Start with this document after extracting the archive. All paths are relative to the extracted `prento` directory.

Read [the measured interpretation](../results/2026-11-04-qa/INTERPRETATION.md) and [the verification record](VERIFICATION.md) for observed outcomes and limitations.

## Scope

This update fixes the sink's artificial one-millisecond minimum sleep, verifies collector admission priority/credit withholding through TCP integration, reports timestamp-based latency decomposition and matched messages, and reruns the original four modes over several workload seeds. It does not implement producer priority, SRPT, actual Homa, durable replay or a production telemetry adapter.

## First verify the bundle

```sh
python3 scripts/verify_bundle.py . --strict
python3 qa/check_evidence.py
```

`MANIFEST.sha256` checks every supplied payload, including source, test logs and raw evidence. `BUNDLE.json` describes the archive: `payload_files` counts all manifest entries including that metadata file, `source_payload_files` excludes generated metadata, and `archive_files` additionally includes the manifest. Use `--strict` before executing or building: it rejects unlisted files. Ordinary verification remains available after deliberate build outputs exist. The adjacent ZIP checksum checks the downloaded archive. These checks detect changed files; they do not authenticate the publisher.

## Prerequisites and reproduction

Native verification requires Linux/WSL, GCC with C++20, Make and Python 3. No third-party C++ or Python libraries are required. Use a fresh output location for local QA logs so the supplied evidence remains unchanged.

```sh
mkdir -p qa-local
make test > qa-local/native.log 2>&1
make sanitize > qa-local/asan-ubsan.log 2>&1
setarch "$(uname -m)" -R make tsan > qa-local/tsan.log 2>&1
python3 scripts/mutation_checks.py > qa-local/mutations.log 2>&1
```

On the implementation host, plain `make tsan` failed before tests with `ThreadSanitizer: unexpected memory mapping`. Per-process `setarch -R` allowed the suite to execute. The initial failure is retained in `qa/logs/tsan.log`; successful workaround runs are separate. No host-wide address-randomization setting was changed. If your platform denies the personality operation or lacks TSan, record that limitation instead of calling it a passing race check. A clean run only covers interleavings actually executed.

The mutation check builds temporary broken copies and expects selected integration tests to fail. Its own successful exit means all three defects were rejected. It never edits repository source.

For a self-contained toolchain, Docker Engine/Desktop must be running with Linux containers. Image builds need access to Ubuntu package repositories unless cached:

```sh
docker build --target qa -t prento:qa-tools .
docker run --rm prento:qa-tools make test
docker run --rm prento:qa-tools make sanitize
```

## Reproduce the benchmark

```sh
docker build --target bench -t prento:qa .
docker run --name fanin-qa-reproduction --cpus 4 --memory 1g --pids-limit 512 --network none --read-only --cap-drop ALL --security-opt no-new-privileges --mount type=volume,source=fanin-qa-reproduction-results,target=/results prento:qa --output /results/multiseed --seeds 7,42,2026 --repeats 3 --duration-ms 5000
docker cp fanin-qa-reproduction:/results/multiseed qa-local/reproduced-results
python3 scripts/report.py qa-local/reproduced-results
```

Use a new container/volume/output name if repeating. The runner deliberately rejects a nonempty results directory. The suite has 144 trials: four scenarios × four modes × three seeds × three repeats, with five seconds of offered load per trial plus drain. Run order is shuffled with order seed 42. The host is shared; container limits do not establish physical isolation. Do not expect identical timings on another machine.

## Evidence map

- `results/2026-11-04-qa/`: corrected-timer trials, environment, raw CSV and generated reports.
- `results/2026-11-04-container/`: preserved historical one-millisecond-floor runs; compare only as history, not as equivalent service-model trials.
- Per-run `run.json`: settings, commands, seed, repetition, sampled RSS/CPU and collector counters.
- `summary.json`: per-run results; `aggregate.json`: equal-run averages and per-seed mean ranges.
- `paired-messages.csv`: every matched message, statuses, pre/post/total intervals and total reduction.
- `paired-comparisons.json`: per-run paired summaries and validation provenance.
- `latency-breakdown.svg`: stacked mean pre/post-send latency.
- `qa/logs/`: native, sanitizer, mutation, Docker-build and benchmark logs, including unsuccessful diagnostic startup attempts.
- `qa/measurement-runner/`: exact scripts extracted from the immutable image that generated the new trials. Subsequent report-validation additions do not change the C++ experiment; the final report is regenerated with the bundled reporter.

## Measurement definitions

For completed messages: pre-send = send timestamp minus intended generation; post-send = completion minus send; total = completion minus intended generation. Pre-send includes scheduling lateness, queueing, preparation and connection setup. Post-send includes transfer, admission/ready waits, sink work and ACK. It is not isolated collector queue time.

All mode comparisons require identical logical IDs, producer assignments, classes, sizes and relative intended schedules, and equal sink/buffer/queue/load/timeout settings. Per-run binary SHA is checked when recorded; older runner metadata supplies one global environment binary SHA instead. The QA image is read-only and its identity is recorded. The reporter labels this provenance distinction.

Means in aggregate tables weight runs equally; per-seed ranges average timing repeats within a seed. Repeats are not independent workload seeds. Paired samples include every matched completed message; there is no post-hoc overload filter. Status changes are counted separately. Percentages compare means and are not per-message average percentages.

Small samples get an observed-maximum label in the report. Empirical p99/p99.9 remain inspectable in JSON; `p99_equals_max` identifies when the order statistic is the maximum. Completion counts and bulk cost must accompany improvements.

## QA acceptance checklist

- Verify supplied file checksums before execution.
- Confirm timer regression catches submillisecond rounding, final remainder, zero duration and cancellation.
- Confirm real collector forwards held-first-ACK workloads as `[1,3,2]` with priority and `[1,2,3]` with FIFO in both admission modes.
- Confirm no credit arrives while the reservation budget is full, and a credit arrives after completion releases space.
- Confirm admission-only, service-only and premature-grant mutations are rejected independently.
- Confirm the separate 192-byte-budget service test waits for both admitted payloads to be ready and verifies priority/FIFO forwarding in both admission modes.
- Confirm report rejects invalid completed timestamps, different logical inputs, duplicate IDs and mismatched experiment settings/binaries.
- Confirm final result matrix is complete and every logical message has one terminal outcome.
- Check reservation peaks and final release, completion fractions, sample sizes and per-seed variation.
- Inspect slow/outage semantics: pauses apply at batch entry; in-progress work is non-preemptive.
- Treat `failed_unknown` as uncertain delivery, not definite loss; completion is simulated processing, not durable storage.
- Record your own review decisions below. No human approval or review is pre-filled.

Failures in NetworkTest cases (including the overload test) retain logs, commands, outcome CSV and captured producer output under `qa-local/failures` (or `FANIN_FAILURE_DIR`). CI uploads that directory on failure. Scheduling/service-order tests use their own cleanup and currently report failures through the test output. The one reported overload-test flake remains unconfirmed; preserve its error and artifacts if it recurs.

## Human QA review record

Reviewer/date: to be completed by QA.

Commands and environment: to be completed by QA.

Findings, decisions and disposition: to be completed by QA.
