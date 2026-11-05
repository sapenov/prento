# Test coverage and limitations

Automated tests exercise the real C++ producer, collector and sink over TCP. AI-assisted review supplements those tests; it does not constitute human QA sign-off.

| Area | What is checked |
|---|---|
| Sink timing | Injected-clock checks cover submillisecond requests, final remainders, zero duration and cancellation. OS wake-up precision is outside the model's control. |
| Admission priority and credits | A 64-byte reservation budget and held first ACK isolate admission order and prevent a grant while capacity is full. |
| Ready-work service order | A separate 192-byte-budget test admits both waiting payloads and waits until they are ready before releasing the first ACK. Priority forwards `[1,3,2]`; FIFO forwards `[1,2,3]`, in both admission modes. |
| Independent sensitivity | Three temporary mutations disable admission priority, disable service priority or grant before reservation. Each is rejected by the relevant integration test. |
| Reports | Reject invalid completed timestamps, duplicate IDs, different logical inputs and mismatched settings or recorded executable identities. Retain completion changes and bulk costs. |
| Archive integrity | Check metadata counts, reject reserved metadata names and verify listed checksums. Strict mode also rejects unlisted files in a fresh extraction. |
| Failure diagnostics | A filesystem fixture verifies NetworkTest artifact retention; CI uploads the directory on failure. Scheduling/service-order failures are reported in test output. |

The suite contains 18 core checks and 26 Python tests. Recorded native, sanitizer and container results are listed in the [verification summary](VERIFICATION.md).

## Open questions

- One externally reported overload-test failure lacks captured error details and has no established root cause. Preserve the error and artifacts if it recurs. No retries or timing relaxations are used to hide it.
- Pre-send timestamps combine several causes. The measured 98.7% burst and 98.1% slow-sink shares do not show how much delay is removable; [producer-latency options](../docs/PRODUCER_LATENCY.md) require separate experiments.
- Credit costs depend on the workload and environment. The main dataset supports “no consistent incremental benefit beyond priority-aware push,” not a universal overhead estimate.
- Kubernetes deployment, physical-network behavior, production telemetry adapters and durable delivery remain unverified.
