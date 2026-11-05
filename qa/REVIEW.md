# Review findings

Findings from AI-assisted review, with implementation decisions and verification evidence.

| Finding | Decision and implementation |
|---|---|
| Service-priority coverage gap | Accepted. Added the supplied two-method test using a 192-byte budget. Both queued payloads are admitted and ready before the held first ACK is released. Admission-only, service-only and premature-grant mutations now have separate sensitivity checks. |
| Headline misses diagnosis | Accepted. README states the measured 98.7% burst / 98.1% slow-sink pre-send shares. Fine-grained pre-send causes remain unmeasured. |
| Credit result varies by environment | Accepted with qualification. Retain measured regressions as observations of the current dataset; use "no consistent incremental win" as the conclusion. Neither 5.39% nor +0.33 ms is a universal cost estimate. |
| One overload-test failure without captured details | Unresolved; no root cause established. NetworkTest cases now retain logs, commands, outcomes, producer output and timeout diagnostics on failure; CI uploads artifacts. No scheduling change, retry or timing relaxation hides the observation. |
| Bundle counts | Fixed. Format 2 distinguishes source_payload_files, payload_files including BUNDLE.json, and archive_files including MANIFEST.sha256. Reserved metadata names are rejected. |
| Unlisted files ignored by verification | Added optional --strict for a fresh extraction. Ordinary verification tolerates intentional subsequent build output while still checking every listed payload. |

Before this change, independent temporary mutations reproduced the specific gap: all 21 old tests passed with service priority disabled; the supplied test failed. With only admission priority disabled, the supplied test passed and the old admission test failed. The new three-mutation checker retains that separation.

The bundle-count, strict-mode and reserved-name fixtures failed before implementation and pass afterward. A real filesystem diagnostic-retention fixture failed before the retention code and passes afterward. The complete updated suite has 18 core checks and 26 Python tests. Sanitizer/mutation/container and artifact details are recorded in VERIFICATION.md and logs/.

The C++ application and measured-source fingerprints are unchanged. Existing 144-trial evidence remains the performance record; adding tests/docs/packaging does not justify generating a replacement headline. Claude's reported independent spot run is corroborating reviewer feedback, not a shipped second complete benchmark matrix.

Producer optimization effort and fair-comparison requirements are in [docs/PRODUCER_LATENCY.md](../docs/PRODUCER_LATENCY.md). That optimization was estimated, not implemented in this update.
