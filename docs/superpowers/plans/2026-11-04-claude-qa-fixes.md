# Claude QA fixes and publication plan

The user authorized the concrete fixes assessed in the preceding review, an effort estimate for producer latency, and creating/publishing a public repository under sapenov if access permits. MIT was selected explicitly. Execute inline; no additional design approval round is needed for these reviewed fixes.

## Scope and design

Keep src/ and include/ unchanged so the existing 144-trial evidence remains applicable. Add the supplied ready-service test beside the admission tests and a separate service-selector mutation. Clarify archive counts and add opt-in strict verification of a fresh extraction; default verification must remain usable after build artifacts exist. Preserve useful process diagnostics on test failure instead of hiding an unconfirmed flake. Explain the pre-send bottleneck and estimate staged improvements without promising gains. Preserve raw experiment outcomes and original private logs; publish sanitized copies of local paths, labeled as such. License MIT; publish only this project, using the existing checkout.

## Review focus

- Ready scheduling must be tested with all three batches admitted, while admission scheduling remains independently tested.
- Strict verification rejects added files; ordinary verification still detects changed/missing payloads and tolerates deliberate build output.
- Bundle metadata counts explicitly distinguish original payloads, metadata and manifest entries, and reserved names cannot replace generated metadata.
- Overload test failures retain diagnostics; no unverified timing change is made to application behavior.
- Public export contains no personal local paths, binaries, caches or credentials; raw CSV/run configuration stays unchanged.

## Tasks

- [x] Add service test, independent admission/service/grant mutations and failure diagnostic retention; run native and sanitizer suites.
- [x] Write failing bundle fixtures, implement clear counts and strict mode; verify the full suite.
- [x] Update README, QA decisions, execution ledger and original completed checkboxes; add MIT and producer-latency estimate.
- [x] Build/test updated Docker QA target and Compose wiring; preserve current evidence and produce a verified sanitized QA ZIP.
- [x] Independent final review; create and push public sapenov/prento if GitHub permissions allow; verify remote contents/CI and report exact status.

The owner selected Prento after naming exploration, with README pronunciation PREN-to and association prompt delivery and operational readiness. Current Docker tags/archive prefix use prento; immutable measurement records retain their original names.
