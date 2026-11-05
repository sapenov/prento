# Agent-assisted implementation record

This file records observed work, not a fictional example. The user asked for a C++ telemetry fan-in lab with fair benchmarks and Docker packaging. The assistant implemented it in the current chat; the user discussed the design through voice. No independent human code review is claimed.

## Context and constraints

The supplied job posting and project evaluations informed DESIGN.md. The user chose C++; the build preserves that choice. A small custom TCP protocol was selected to avoid external C++ dependencies. Actual Homa, cloud spending, switch installation, Kafka, Iceberg and production traffic remain out of scope. Four combinations isolate priority from receiver credits.

## Verification gates used

- Core reservation/scheduling tests were compiled before the core header existed; compilation failed as expected, then the implementation passed.
- Process integration tests were created before the application executable existed, then run against real producer/collector/sink processes. No transport mocks.
- Reporter tests initially failed because the reporter was absent. Literal outcome fixtures check byte conservation, unknowns, drops and percentiles.
- GCC warnings are errors. The first application build caught misleading indentation in sink shutdown; this was corrected before running the process tests.
- Native networking was initially blocked by the execution sandbox. Local-loopback test execution was approved through the environment's approval mechanism.
- Docker Desktop was initially stopped. It was started for local build/testing; no deployment or external registry publication was performed.

## Actual findings and changes

1. Pilot execution showed no large credit advantage beyond priority-aware push in the small workload. No predicted 80–90% claim was inserted into results.
2. A new idle-connection test reproduced a failed first batch after the sink closed an idle persistent connection at one second. Extending the idle allowance only postponed the problem. A second low-rate-producer regression exposed the same issue at collector input. Both servers now poll idle sessions without a frame deadline, then enforce a deadline once frame bytes start arriving. Transport failure still reports unknown outcome rather than silently retrying.
3. Strict CLI validation was missing. Unknown options could start incorrectly configured services. Command-specific allowlists were added, and producer inputs are parsed before worker creation.
4. A shutdown test reproduced a producer remaining asleep after SIGTERM during a long scheduled wait. Scheduled waits now check a lock-free atomic stop flag at short intervals.
5. Independent read-only code review (one subagent, required by the review skill) found retained completed session threads. A reaping thread owner now joins finished sessions during normal operation; live peer caps remain enforced.
6. The reviewer identified a redundant `mkdir /results` in the inherited benchmark image and missing Kubernetes emptyDir write permissions. The directory creation is idempotent; the example Job uses fsGroup.
7. Review clarified the current sink model: slowdown and outage-like pauses are applied at batch entry, not mid-batch. Documentation now states that limitation, along with fitting-only bulk fairness and producer-local head-of-line blocking.

## Initial-version checks

Final native regression, ASan/UBSan, both Docker build targets, the Compose demo, and the final 48-trial benchmark passed. Exact scope and outcomes are recorded in [VERIFICATION.md](VERIFICATION.md). Kubernetes cluster execution and ThreadSanitizer were not run.

## Authorized timer and QA update

The user subsequently requested the timer correction, integration tests, latency breakdown, several benchmark seeds and a QA archive. The deterministic timer regression first rejected the old one-millisecond rounding behavior. The helper now sleeps for the smaller of remaining duration and one millisecond; this removes the artificial floor without claiming precise OS wake-ups.

A controlled TCP backend holds the first processing ACK while two more clients announce work. Metrics establish arrival order and a full reservation budget. Tests observe priority overtaking, FIFO order and credit withholding/resumption against the real collector. Two temporary source mutations disable priority and grant before reservation; each was rejected by the relevant integration test. Those expected failures appear in the mutation log and are not uncorrected source defects.

Reporter fixtures verify timestamp decomposition and paired logical workloads. Review identified missing equal-settings validation; the reporter now rejects inconsistent sink/load/buffer/queue/timeout settings and executable identities. Legacy metadata explicitly uses one global executable SHA rather than pretending to have per-run binary hashes. Neither post-send time nor pre-send time is labeled pure queue time.

Plain ThreadSanitizer startup failed with an unexpected memory mapping on this WSL host. A per-process `setarch -R` retry ran the core and process suites successfully; the initial failure and successful retry are both retained. No host-wide ASLR configuration changed. Final native, ASan/UBSan and TSan Python suites each passed 21 tests. The independent read-only reviewer found no remaining Important/Critical issues after fixes; final evidence and packaging checks are recorded separately in [qa/VERIFICATION.md](../qa/VERIFICATION.md).

## What the implementation does not prove

No claim of protocol novelty, stable short-run p99, production scale, durable completion, exactly-once delivery, automatic alert classification or on-switch compatibility. Tests sample executions; they do not constitute a proof over every possible interleaving or failure pattern.

Final artifact verification caught two orchestration mistakes: a reporter started before Docker copying finished and rejected an incomplete group; an archive check started before the ZIP writer finished and found no archive. Both were rerun only after the producing command exited. The completed evidence audit and clean extracted build passed; the failed report attempt is retained in the logs. The final archive was rebuilt to include the clean-extraction log, then checked again for integrity.

## Claude-review fixes and authorized publication

The user accepted the assessed review fixes and selected MIT. A new ready-service integration test and separate admission/service/grant mutations now cover both selectors independently. Native, ASan/UBSan, TSan (per-process ASLR workaround), and the Docker QA suite each passed 26 Python tests; native/sanitizer/container core checks passed. Compose delivered 300/300 and shut down. Current application fingerprints still match the measured image, so the existing multi-seed experiment was audited and retained rather than rerun for test-only changes.

New package fixtures demonstrated wrong metadata counts, missing strict verification and allowed reserved names before fixes. An actual failed-test fixture reproduced deletion of diagnostics before retention was added. NetworkTest failures now retain commands, output, logs, timeout information and outcomes; CI uploads them on failure. The isolated reported flake remains unconfirmed.

Public copies of logs normalize local workspace prefixes while retaining failed checks and benchmark numbers; original local copies are excluded under qa-private. Producer scheduling alternatives and effort estimates are documented separately; no producer optimization is claimed implemented. GitHub identity and CLI authentication both resolved to sapenov, and the requested repository name was available at the initial check. Publication status is recorded after the actual remote operation.

The owner selected the public name Prento and requested its pronunciation and association. README now states PREN-to, prompt delivery and operational readiness. Public Docker examples and the archive prefix use prento; historical measurement tags/records stay unchanged. Archive tests first rejected the missing new extraction prefix, then passed after the packager update. C++ sources, executable name and CMake measurement fingerprint stay unchanged.

Initial publication whitespace checking flagged retained CSV CRLF endings and console progress formatting. The raw evidence was preserved. Git attributes now prevent checkout/newline transformations and exempt only raw results/log formatting from whitespace checks; source checks pass. Every staged blob was independently compared with local bytes. The named Prento extraction passed its strict manifest, complete evidence audit and all core/Python tests before publication.
