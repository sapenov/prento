# Measured application source

This snapshot preserves the application and CMake files identified by [the 144-trial benchmark fingerprints](../measurement-runner/source-sha256.json). Original paths, identifiers and metric names are retained. `SOURCE.json` records the source commit and the accompanying core-test hash.

The repository's live executable, environment variables, metrics, headers and C++ namespace use `prento` / `PRENTO`. These names change source and executable fingerprints. The benchmark results describe this snapshot and its recorded image, rather than a measurement of a newly built binary.

To build the measured application from the repository root:

```sh
cmake -S qa/measurement-source -B build/measured-source
cmake --build build/measured-source
ctest --test-dir build/measured-source --output-on-failure
```

The snapshot executable retains its recorded name. Building it locally does not reproduce the exact recorded image or executable hash; compiler and build settings affect those identities. Use the [measurement provenance](../measurement-runner/README.md) to inspect the measured image.
