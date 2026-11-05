# Measurement provenance

This directory identifies the image and application used for the 144-trial benchmark.

| File | Purpose |
|---|---|
| `bench.py`, `report.py` | Exact runner scripts captured from the measured image; audit copies |
| `source-sha256.json` | Fingerprints of the application sources and CMake configuration |
| `image-inspect.json`, `final-images-inspect.json`, `container-inspect.json` | Immutable image identity, runtime limits and container state |

Use `scripts/report.py` at the repository root to render reports. It validates matched logical inputs, configuration and recorded executable identities without modifying raw outcomes or run configurations.

The measured runner records one executable SHA-256 in the benchmark's `environment.json`. Its reports label the identity source `global-environment`. The repository runner can also record per-run executable SHA values. A suite-level identity and a per-run identity provide different provenance; the reporter makes that distinction explicit.

The supplied application matches the measured-source fingerprints. Container inspection records include the state after benchmark exit. The source ZIP contains no compiled image or binary; build using the supplied Dockerfile.
