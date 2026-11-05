# Measurement provenance

`bench.py` and `report.py` here were extracted from the immutable benchmark image that executed the 144 trials. They are retained for audit; use `scripts/report.py` for the final report.

After measurement started, the current runner gained per-run binary SHA metadata and the reporter gained stricter configuration/binary checks and neutral historical timer wording. The measured image already captured a global executable SHA in environment.json. The final reporter explicitly labels its use of that global identity, and the final report was regenerated locally without changing raw outcomes or run configurations.

`source-sha256.json` fingerprints the application sources and CMake configuration used to build the corrected benchmark. These application files were unchanged during measurement. Container and image inspection records identify the actual immutable image and limits. The final container inspection is captured after exit. No image binary is included in the source ZIP; rebuild using the supplied Dockerfile.
