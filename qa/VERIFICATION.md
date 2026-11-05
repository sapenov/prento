# Verification summary

Recorded validation: November 5, 2026 (America/New_York). Reproduction commands are in the [QA guide](README.md).

## Tests and deployment checks

Evidence paths below are relative to `qa/logs/validation/`.

| Check | Recorded result | Evidence |
|---|---|---|
| README and results figure | Source-value, local-link/anchor and integrity checks passed; normal/narrow/grayscale inspection; native suite and short Compose comparison passed | `../readme-validation.log` |
| Native warnings-as-errors build | 18 core checks and 26 Python tests passed | `native.log` |
| ASan/UBSan | 18 core checks and 26 Python tests passed | `asan-ubsan.log` |
| TSan | 18 core checks and 26 Python tests passed with per-process `setarch -R` | `tsan.log` |
| Mutation checks | Admission-priority, service-priority and premature-grant defects independently rejected | `mutations.log` |
| Docker QA build and tests | Build passed; 18 core checks and 26 Python tests passed | `docker-qa-build.log`, `docker-qa-tests.log` |
| Runtime and benchmark images | Both targets built; benchmark entrypoint completed all four modes | `docker-runtime-build.log`, `docker-bench-build.log`, `docker-bench-smoke.log` |
| Compose runtime | Configuration passed; 300/300 messages completed, no drops or unknowns; isolated stack removed | `compose.log` |
| Clean QA extraction | Strict checksums, original 144-trial audit, fresh build, 18 core checks and 26 Python tests passed | `bundle.log` |
| Measured-source snapshot | CMake build and core tests passed using the Docker toolchain | `cmake.log` |
| Functional benchmark smoke | 144 short trials, 1,620/1,620 messages; input, accounting and latency checks passed | `benchmark-smoke.log`, `smoke-evidence.json` |
| Source and evidence integrity | Measured source matches recorded hashes; live application differs by naming substitutions only; supplied benchmark evidence unchanged | `provenance.json` |

The functional smoke uses 100-millisecond load windows in a separate local directory. It verifies the renamed executable, metrics and reporting, and is not performance evidence for the published results. The live application exposes `prento_` metrics; the evidence checker also reads the recorded metric names without rewriting them.

The host has no native CMake installation; Docker supplies that toolchain. On WSL, TSan uses per-process `setarch -R` to avoid memory-mapping startup failures. A separate test-discovery attempt failed to resolve the working directory before tests ran; `tsan-startup.log` retains that diagnostic, and `tsan.log` records the complete successful suite. Sanitizer passes cover executed paths and interleavings, not all possible races.

The [CI workflow](../.github/workflows/ci.yml) runs native tests, sanitizers and the runtime Docker build. [Coverage notes](REVIEW.md) describe independent admission/service-order tests and the unconfirmed overload-test failure. [Log handling](logs/README.md) describes local-path normalization.

## Main benchmark: 144 trials

Four scenarios × four modes × three seeds (7, 42, 2026) × three repeats, with five-second offered-load windows plus drain. The benchmark container exited successfully without OOM.

- All **79,236 generated messages completed**; no producer drops or delivery-unknown outcomes.
- All 144 reservation peaks stayed within **262,144 bytes**; final reservations and announcement/ready queues were zero.
- The evidence checker verified matching logical inputs and settings, timestamp decomposition and outcome accounting across 36 four-mode groups. Evidence: `qa/logs/validation/evidence.json`.
- Individual runs contain **22–45 critical messages**; nearest-rank p99 selects the observed maximum in every run. These samples do not establish a tail SLO.

Separate producer, collector and sink processes communicate over loopback inside one container capped at four CPUs, 1 GiB and 512 PIDs. External networking is disabled; the image is read-only, all capabilities are dropped and no-new-privileges is set. The shared WSL host reports Intel Core i9-10885H and 16 logical CPUs. Measurement ran 02:09:33–02:24:01 UTC on November 5, 2026 (November 4 locally).

Measured image: `sha256:715886aabb9b466e3185cdf24f1c465c73d2199220a935b9ef570c0dc063c9ce`.

Executable SHA-256: `7a844add79b6ae3998723349261b64f994e8a9e4967c700a2c5a7ea94771e1a2`.

[Measurement provenance](measurement-runner/README.md) supplies image/container inspection and application-source fingerprints. Those fingerprints identify the [measured application snapshot](measurement-source/README.md). The live source uses Prento identifiers and produces a different executable identity; the performance results apply to the recorded image. The measured runner records executable identity once in `environment.json`; reports explicitly label that suite-level identity as `global-environment`. Raw outcome and run-configuration files retain their measured bytes.

Read the [findings](../results/2026-11-04-qa/INTERPRETATION.md), [complete report](../results/2026-11-04-qa/REPORT.md) and [environment](../results/2026-11-04-qa/environment.json) together.

## Dataset comparability and limits

The [48-trial reference dataset](../docs/VERIFICATION.md) uses seed 42, three-second load windows and a one-millisecond minimum sink sleep. The main 144-trial dataset uses three seeds, five-second windows and sleeps bounded by the remaining requested duration. OS scheduling can extend actual sleeps. These are different service/load configurations; their difference cannot isolate a timer-related speedup.

This is a custom-protocol laptop experiment. Completion is simulated processing, not durable storage. Sink pauses act at batch entry, batches are non-preemptive and producer-local FIFO blocking remains. Sampled RSS omits some kernel buffering. Kubernetes configuration has not been deployed or measured. The results establish neither production capacity nor multi-node scale.
