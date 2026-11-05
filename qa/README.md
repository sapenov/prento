# QA guide

Verify the files, run the tests, then inspect or reproduce the benchmark. Commands below run from the repository root or the extracted `prento/` directory.

## 1. Verify the supplied evidence

```sh
# ZIP extraction only: run before building or generating files.
python3 scripts/verify_bundle.py . --strict

# Repository or ZIP: validate all 144 benchmark trials.
python3 qa/check_evidence.py
```

The ZIP's adjacent `.sha256` file checks the archive; `MANIFEST.sha256` checks its extracted files. Strict verification also rejects unlisted files. Omit `--strict` to recheck supplied files after deliberate builds. Checksums detect changes; they do not authenticate the publisher.

## 2. Run the tests

Requirements: Linux/WSL, GCC with C++20, Make and Python 3. No third-party C++ or Python libraries are required. Save local output outside the supplied evidence:

```sh
mkdir -p qa-local
make test > qa-local/native.log 2>&1
make sanitize > qa-local/asan-ubsan.log 2>&1
setarch "$(uname -m)" -R make tsan > qa-local/tsan.log 2>&1
python3 scripts/mutation_checks.py > qa-local/mutations.log 2>&1
```

Expected: 18 core checks and 27 Python tests pass in each suite. The mutation checker succeeds when tests reject all three deliberate defects: disabled admission priority, disabled service priority and a premature credit grant. It builds temporary copies without editing repository source.

On the measured WSL host, TSan requires per-process `setarch -R` to avoid an `unexpected memory mapping` startup failure. If that operation or TSan is unavailable, record the race check as not run. Sanitizers cover only executed paths and interleavings.

Docker provides the toolchain if preferred; image builds require package-repository access unless cached:

```sh
docker build --target qa -t prento:qa-tools .
docker run --rm prento:qa-tools make test
docker run --rm prento:qa-tools make sanitize
```

## 3. Inspect the results

| File or directory | Purpose |
|---|---|
| [VERIFICATION.md](VERIFICATION.md) | Recorded test results, benchmark checks and execution limits |
| [REVIEW.md](REVIEW.md) | What the tests establish and what remains unverified |
| [Benchmark findings](../results/2026-11-04-qa/INTERPRETATION.md) | Main conclusions, trade-offs and sample-size limits |
| [Benchmark report](../results/2026-11-04-qa/REPORT.md) | Complete 144-trial tables and latency breakdown |
| `results/2026-11-04-qa/` | Raw trials, environment, charts and machine-readable summaries |
| [measurement-source/](measurement-source/README.md) | Exact application source for the recorded benchmark; separate from live Prento source |
| [measurement-runner/](measurement-runner/README.md) | Measured image identity, source fingerprints and captured runner scripts |
| [logs/](logs/README.md) | Test and execution logs; the verification summary identifies the relevant files |
| [Reference dataset](../docs/VERIFICATION.md) | Separate 48-trial configuration with a one-millisecond sink sleep floor |

Within a benchmark directory:

| File | Contents |
|---|---|
| `environment.json` | Machine, container and executable identity |
| Per-trial `outcomes.csv` / `run.json` | Every message outcome; exact commands, configuration, process samples and collector counters |
| `summary.json` / `aggregate.json` | Per-run statistics; equal-run means and per-seed mean ranges |
| `paired-messages.csv` / `paired-comparisons.json` | Matched messages and per-run comparisons, including completion-status changes |
| `latency-breakdown.svg` | Mean pre-send and post-send latency by scenario and mode |

Pre-send time runs from intended generation to send and includes scheduling lateness, producer waiting, preparation and connection setup. Post-send time includes transfer, admission/ready waits, sink processing and ACK. Their sum is end-to-end latency; neither interval isolates collector queueing. Run means are weighted equally. Seed ranges describe three workloads, not confidence intervals.

## 4. Reproduce the benchmark

```sh
mkdir -p qa-local
docker build --target bench -t prento:bench .
docker run --name prento-reproduction --cpus 4 --memory 1g --pids-limit 512 --network none --read-only --cap-drop ALL --security-opt no-new-privileges --mount type=volume,source=prento-reproduction-results,target=/results prento:bench --output /results/multiseed --seeds 7,42,2026 --repeats 3 --duration-ms 5000
docker cp prento-reproduction:/results/multiseed qa-local/reproduced-results
python3 scripts/report.py qa-local/reproduced-results
```

This runs four scenarios × four modes × three seeds × three repeats: 144 trials, each with five seconds of offered load plus drain. Order seed 42 shuffles the suite. On the measured laptop it took about 15 minutes. Use fresh container, volume and output names for another run; nonempty result directories are protected. Timings vary across hosts and runs.

For a three-container demo, follow the [running guide](../docs/RUNNING.md#three-service-demo). Kubernetes configuration is illustrative and has not been deployed or benchmarked.

## Acceptance and failure reporting

Check completion/drop/unknown counts, reservation peaks and final release alongside latency, bulk cost and per-seed variation. Small critical sample counts make p99 an observed maximum, not a tail guarantee. Sink pauses apply at batch entry; processing is non-preemptive. ACK means simulated processing, not durable storage. `failed_unknown` means uncertain delivery.

NetworkTest failures retain commands, logs, outcomes and producer output under `qa-local/failures` or `PRENTO_FAILURE_DIR`; CI uploads that directory on failure. Scheduling/service-order tests report failures in test output. Report the command, environment, error and available artifacts. A reviewer can record findings locally; the supplied evidence does not constitute human QA sign-off.
