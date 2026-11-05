# Verification summary

Recorded validation: November 4, 2026 (America/New_York). Reproduction commands are in the [QA guide](README.md).

## Tests and deployment checks

| Check | Recorded result | Evidence in `qa/logs/` |
|---|---|---|
| Native warnings-as-errors build | 18 core checks and 26 Python tests passed | `prento-native.log` |
| ASan/UBSan | 26 Python tests passed against the instrumented application; 18 sanitized core checks also passed | `prento-asan-ubsan.log`, `claude-fixes-asan-ubsan.log` |
| TSan | 26 Python tests passed against the instrumented application; 18 sanitized core checks also passed; per-process `setarch -R` required | `prento-tsan.log`, `claude-fixes-tsan.log` |
| Mutation checks | Admission-priority, service-priority and premature-grant defects independently rejected | `claude-fixes-mutations.log` |
| Docker QA build and tests | Build passed; 18 core checks and 26 Python tests passed | `prento-docker-build.log`, `prento-docker-tests.log` |
| Compose runtime | Build and configuration passed; 300/300 messages completed, no drops or unknowns; stack shut down | `prento-runtime-build.log`, `prento-compose.log` |
| Clean ZIP extraction | Strict checksums, 144-trial evidence audit, fresh build, 18 core checks and 26 Python tests passed | `prento-clean-extraction.log` |
| GitHub Actions | Native, ASan/UBSan, TSan and runtime Docker build passed on commit `d62053f` | [CI run](https://github.com/sapenov/prento/actions/runs/41965080263), `prento-github-ci.json` |

Plain TSan startup on the WSL host failed with `unexpected memory mapping` (`tsan.log`). Per-process `setarch -R` allowed test execution without changing host-wide settings. Sanitizer passes cover executed paths and interleavings, not all possible races.

The [coverage notes](REVIEW.md) explain independent admission/service-order tests and the unconfirmed overload-test failure. Public logs normalize local path prefixes; [log handling](logs/README.md) describes the transformation.

## Main benchmark: 144 trials

Four scenarios × four modes × three seeds (7, 42, 2026) × three repeats, with five-second offered-load windows plus drain. The benchmark container exited successfully without OOM.

- All **79,236 generated messages completed**; no producer drops or delivery-unknown outcomes.
- All 144 reservation peaks stayed within **262,144 bytes**; final reservations and announcement/ready queues were zero.
- The evidence checker verified matching logical inputs and settings, timestamp decomposition and outcome accounting across 36 four-mode groups. Evidence: `qa/logs/claude-fixes-evidence.json`.
- Individual runs contain **22–45 critical messages**; nearest-rank p99 selects the observed maximum in every run. These samples do not establish a tail SLO.

Separate producer, collector and sink processes communicate over loopback inside one container capped at four CPUs, 1 GiB and 512 PIDs. External networking is disabled; the image is read-only, all capabilities are dropped and no-new-privileges is set. The shared WSL host reports Intel Core i9-10885H and 16 logical CPUs. Measurement ran 02:09:33–02:24:01 UTC on November 5, 2026 (November 4 locally).

Measured image: `sha256:715886aabb9b466e3185cdf24f1c465c73d2199220a935b9ef570c0dc063c9ce`.

Executable SHA-256: `7a844add79b6ae3998723349261b64f994e8a9e4967c700a2c5a7ea94771e1a2`.

[Measurement provenance](measurement-runner/README.md) supplies image/container inspection and application-source fingerprints. Those fingerprints match the supplied application. The measured runner records executable identity once in `environment.json`; reports explicitly label that suite-level identity as `global-environment`. Raw outcome and run-configuration files retain their measured bytes.

Read the [findings](../results/2026-11-04-qa/INTERPRETATION.md), [complete report](../results/2026-11-04-qa/REPORT.md) and [environment](../results/2026-11-04-qa/environment.json) together.

## Dataset comparability and limits

The [48-trial reference dataset](../docs/VERIFICATION.md) uses seed 42, three-second load windows and a one-millisecond minimum sink sleep. The main 144-trial dataset uses three seeds, five-second windows and sleeps bounded by the remaining requested duration. OS scheduling can extend actual sleeps. These are different service/load configurations; their difference cannot isolate a timer-related speedup.

This is a custom-protocol laptop experiment. Completion is simulated processing, not durable storage. Sink pauses act at batch entry, batches are non-preemptive and producer-local FIFO blocking remains. Sampled RSS omits some kernel buffering. Kubernetes configuration has not been deployed or measured. The results establish neither production capacity nor multi-node scale.
