# Execution ledger — plan: docs/superpowers/plans/2026-11-04-fanin-lab.md

2026-11-04: Read supplied discussions and selected four-mode fan-in lab. Existing folder is not a git checkout; isolate in a new sibling project directory. No worktree or branch mutation needed.

Ruling: use inline execution under the user's request to build the complete solution; no additional design approval round. No subagents unless required by a later review skill.

Environment: GCC 13.3 and Make available; CMake and Boost headers absent. Docker command currently fails with WSL vsock error. Use dependency-free native compilation first and report container execution separately.

Pre-flight: core APIs are consumed by collector and unit tests; wire types are shared by all executable modes; CSV fields are consumed by reporter and integration tests. Declare interfaces in code and keep consumers consistent.

Task 1: complete — 14 core checks, including budget invariant and thread-handle reclamation.
Task 2: complete — real TCP application and 11 Python checks pass; all four modes, invalid data, backend failure, idle sessions and SIGTERM verified. ASan/UBSan passed against the same source.
Task 3: complete — native 16-run pilot and final fixed-budget Docker 48-run suite complete. All15,852 generated messages completed; no blanket credit advantage found. Raw evidence copied into results/2026-11-04-container.
Task 4: complete — runtime and benchmark targets build, Compose delivered 300/300, final regression and ASan/UBSan pass. Kubernetes example is documentation-only; no cluster execution claim. Initial local Git repository was created on the historical branch codex/fanin-lab. Public publication under sapenov was authorized later; see the QA-fixes ledger below.

Ruling: final source uses full-batch scheduling, not SRPT; preserves fair baselines while controlling implementation size. Admission timeout and unknown delivery are explicit outcomes. Fitting-only fairness and batch-entry sink intervals are documented limits.

QA-fixes ledger: user authorized service-selector coverage, bundle verification fixes, public preparation and a producer-latency effort estimate. MIT was chosen explicitly. Application sources remain unchanged; the 144-trial evidence is retained without a new performance claim. Bundle fixtures failed on wrong counts, reserved metadata and absent strict mode, then passed after fixes. A diagnostic-retention fixture failed before implementation, then passed.

QA-fixes verification: native, ASan/UBSan, TSan and Docker each passed 18 core checks plus 26 Python tests; three selector/grant mutations rejected; Compose delivered 300/300. Independent review found no Important/Critical findings; sensitivity arithmetic uses unrounded aggregate means, and diagnostic-retention wording was narrowed to NetworkTest cases. Public selection scan passed before publication.

Prento: the user selected this name and requested pronunciation/association in README. Public destination https://github.com/sapenov/prento was created successfully under the authenticated sapenov account. Current Docker/Compose/native/sanitizer checks passed with the renamed presentation; original C++ and raw experiment records remain unchanged.

Publication complete: public sapenov/prento on main, MIT recognized by GitHub. The corrected GitHub Actions run 41965080263 passed native, sanitizer and Docker checks; its initial job-context validation failure was corrected in d62053f. README pronunciation/association verified remotely. Independent final review and named clean-extraction QA checks passed.
