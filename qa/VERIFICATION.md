# QA verification

Validation was performed on November 4, 2026. Current and historical test evidence are distinguished below; raw experiment records are preserved separately.

## Current regression coverage

The C++ application fingerprints still match the measured 144-trial image. This revision changes tests, packaging, CI diagnostics, documentation and licensing. It adds independent service-order coverage; the older coverage limitation below is retained as history.

| Check | Observed result | Evidence under qa/logs/ |
|---|---|---|
| Native | 18 core checks and 26 Python tests passed | claude-fixes-native.log |
| ASan/UBSan | 18 core checks and 26 Python tests passed | claude-fixes-asan-ubsan.log |
| TSan with per-process setarch -R | 18 core checks and 26 Python tests passed | claude-fixes-tsan.log |
| Three independent mutants | Admission priority, service priority and premature grants each rejected; checker exit 0 | claude-fixes-mutations.log |
| Docker QA build and test | Build passed; 18 core checks and 26 Python tests passed in container | claude-fixes-docker-build.log, claude-fixes-docker-tests.log |
| Compose validation and demo | Configuration valid; 300 generated/completed, no drops or unknowns; shut down | claude-fixes-compose.log |
| Preserved experiment audit | 144 trials, 36 groups, 79,236 completions, reservation/queue and matched-input invariants passed | claude-fixes-evidence.json |

The new bundle fixtures first failed for incorrect metadata count, missing strict verification and allowed reserved names; they pass after correction. The diagnostic fixture first failed because files were deleted, then passed once a failing process test retained its real files. No application timing changes or test retries were introduced for the unconfirmed overload-test flake.

A clean temporary extraction of the updated archive passed strict verification, the complete evidence audit, and a fresh warnings-as-errors build with all 18 core checks and 26 Python tests. Log: `qa/logs/claude-fixes-clean-extraction.log`. The log accompanies the source and evidence in the QA bundle.

Review decisions: [REVIEW.md](REVIEW.md). Public logs retain execution outcomes and replace local workspace prefixes; [log handling](logs/README.md) documents the transformation. Original execution logs are retained locally; supplied copies are covered by the archive manifest. Prento is MIT licensed.

## Current project checks

Current archive roots/image examples use prento; historical measurement records retain their earlier identifiers. Source: [sapenov/prento](https://github.com/sapenov/prento), licensed under MIT.

After renaming, native and Docker suites passed 18 core checks and 26 Python tests. All 26 Python tests also passed against the unchanged ASan/UBSan and TSan binaries (TSan with per-process ASLR disabled). The renamed Compose stack built and completed 300/300 messages with no drops/unknowns, then shut down. Evidence: prento-native.log, prento-asan-ubsan.log, prento-tsan.log, prento-docker-build.log, prento-docker-tests.log, prento-runtime-build.log and prento-compose.log under qa/logs/.

The Prento-named clean extraction passed strict verification, the full 144-trial audit and a fresh build with 18 core checks/26 Python tests. Log: `qa/logs/prento-clean-extraction.log`. Git attributes preserve exact source/evidence bytes; whitespace checks exclude retained raw report/log formatting. A staged-byte audit verified every file against its Git blob before publication.

Public GitHub verification: [the corrected run](https://github.com/sapenov/prento/actions/runs/41965080263) passed native tests, ASan/UBSan, TSan and runtime Docker build on commit d62053f. The initial validation failure remains visible in history and its configuration fix is recorded in ENGINEERING.md. Subsequent public README/handoff edits are documentation only and use skip-ci commits; no application/test source changed after the passing run. Structured evidence: `qa/logs/prento-github-ci.json`.

## Previous corrected-timer QA revision (historical)

The following record and its logs describe the earlier 21-test revision. Its raw performance measurements are still current because application sources are unchanged.

## Previous source and regression checks

| Check | Observed result | Evidence |
|---|---|---|
| Native warnings-as-errors build and suite | 18 core checks and 21 Python tests passed | `qa/logs/native-final.log` |
| AddressSanitizer + UndefinedBehaviorSanitizer | 18 core checks and full final Python suite passed | `qa/logs/asan-ubsan.log`, `qa/logs/asan-ubsan-final.log` |
| Plain ThreadSanitizer startup | Failed before test execution: unexpected memory mapping | `qa/logs/tsan.log` |
| ThreadSanitizer with per-process ASLR disabled | 18 core checks and full final Python suite passed | `qa/logs/tsan-no-aslr.log`, `qa/logs/tsan-final.log` |
| Mutation checks | Both deliberate defects rejected; checker exited successfully | `qa/logs/mutation-checks.log` |
| Multi-seed orchestration smoke | Eight short trials completed | `qa/logs/benchmark-smoke.log` |
| Independent read-only source review | Prior configuration/provenance issues fixed; no remaining Important/Critical findings | `docs/ENGINEERING.md` |

Timer tests first rejected the old submillisecond rounding behavior. Integration tests use the actual collector and controlled TCP clients/backend. In that earlier revision they isolated admission scheduling and credit reservation. The current revision separately exercises admitted payload-ready service ordering. Intentional failing test output in the mutation log belongs to temporary mutated source, not the shipped implementation.

Successful sanitizers cover executed paths/interleavings only. Release benchmarks use an uninstrumented binary. No host-wide ASLR setting was changed; QA should record any platform restriction that prevents the documented TSan workaround.

## Operational limits

This remains an application-layer, custom-protocol laptop lab. A sink ACK denotes simulated processing, not durable storage. Outage-like pauses and slowdown changes act at batch entry; batches are non-preemptive. Producer-local FIFO blocking remains. RSS sampling does not include all kernel buffering. The Kubernetes manifest is supplied and reviewed statically, not deployed or measured. No actual Homa, switch software installation, OTLP/gNMI adapter, Kafka replay or multi-node scale claim is made.

## Corrected container evidence

- Final QA toolchain image build and container-native suite passed: 18 core checks and 21 Python tests. Logs: `docker-qa-build-final.log`, `docker-native-final.log` under `qa/logs/`.
- Final runtime image build and Compose validation passed. The three-service demo generated/completed 300 messages with no drops/unknowns, then shut down cleanly. Logs: `docker-runtime-build-final.log`, `compose-demo-final.log`.
- The fixed-budget benchmark exited 0 without OOM: 144/144 trials; workload seeds 7, 42, 2026; three timing repeats; four modes and four scenarios; five-second offered windows plus drain.
- All 79,236 logical messages completed. All 144 reservation peaks were within 262,144 bytes; all final reservation/announcement/ready queues were zero. The evidence checker also verified logical input/configuration matches and timestamp decomposition across 36 four-mode groups. Log: `qa/logs/evidence-check.json`.
- Individual runs contain 22–45 critical samples. All empirical critical p99s select their observed maximum; no tail guarantee is claimed.

Measured image: `sha256:715886aabb9b466e3185cdf24f1c465c73d2199220a935b9ef570c0dc063c9ce`. Executable SHA-256: `7a844add79b6ae3998723349261b64f994e8a9e4967c700a2c5a7ea94771e1a2`.

Container limits: four CPUs (`cpu.max=400000 100000`), 1 GiB (`memory.max=1073741824`), PID limit 512; no external network; read-only image, all capabilities dropped, no-new-privileges. The application uses loopback TCP between separate processes. The shared WSL host reports Intel Core i9-10885H and 16 logical CPUs. Measurement ran 02:09:33–02:24:01 UTC November 5 (November 4 locally).

`qa/measurement-runner/` retains exact image scripts, image/container inspection and application-source fingerprints. The final reporter uses the global environment binary identity because the measured runner predates the later per-run SHA metadata addition; this distinction is explicit in paired-comparisons.json. Raw CSV and run.json files were not modified. An initial report-regeneration attempt ran before the Docker copy finished and rejected an incomplete four-mode group; its failed log is retained. The completed-copy regeneration and evidence audit passed.

Results and numerical limits: [interpretation](../results/2026-11-04-qa/INTERPRETATION.md), [complete report](../results/2026-11-04-qa/REPORT.md), [raw environment](../results/2026-11-04-qa/environment.json). Historical results used a different timer and load-window length; no isolated timer-fix speedup is inferred from them.

An independent read-only evidence review recomputed all 144 raw ledgers, aggregate means/seed ranges, 144 paired comparison records and 79,236 paired-message rows. It also checked source fingerprints and SVG structure. No Important/Critical findings remained. The review was AI-assisted; automated checks and measured outcomes are listed separately.

## Archive verification

A clean temporary extraction passed the archive exclusion check, every payload checksum, the complete 144-trial evidence audit, and a fresh warnings-as-errors build plus all 18 core checks/21 Python tests. Log: `qa/logs/clean-bundle-verification.log`. The final archive is rebuilt to include this log and the completed verification record; payload checksums and ZIP CRC are checked again afterward. No source code changed between that clean build and final packaging.

The ZIP includes complete source/configuration/tests, current and historical raw trials, generated reports and charts, exact measurement-runner scripts/provenance, reproduction commands, successful and failed diagnostic logs, and an unfilled human QA checklist. It excludes `.git`, compiled binaries, caches and unrelated workspace files. The adjacent `.zip.sha256` verifies the final archive; `MANIFEST.sha256` verifies its extracted payloads. These are integrity checks, not publisher authentication.
