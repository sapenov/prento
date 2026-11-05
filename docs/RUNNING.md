# Running Prento

Commands run from the repository root. For the primary comparison workflow, start with the [README quickstart](../README.md#quickstart).

## Three-service demo

Requirements: Docker Desktop with Linux containers (WSL2 on Windows), or Docker Engine and Compose on Linux. The build image contains the compiler and CMake.

```sh
docker compose build
docker compose up -d sink collector
docker compose run --rm producer
docker compose logs collector
```

Retrieve the raw outcomes from the named results volume with:

```sh
docker compose run --rm --entrypoint cat producer /results/outcomes.csv
docker compose down
```

Collector metrics and health: [http://localhost:19090/metrics](http://localhost:19090/metrics), `/readyz`, `/livez`. Health means the process can accept connections; it does not establish sink durability or upstream health. Service containers run as non-root with dropped capabilities, read-only root filesystems and fixed resource limits. Only the metrics port is published, on loopback.

Choose the mode before starting the stack:

```sh
ADMISSION=push POLICY=fifo docker compose up -d --force-recreate sink collector
ADMISSION=push POLICY=fifo docker compose run --rm producer
```

Keep producer and collector admission settings identical. On PowerShell use `$env:ADMISSION="push"; $env:POLICY="fifo"` before the Compose commands. Start fresh services for a fresh slowdown schedule.

## One-command experiment

Run all four policies over steady, burst, slow-sink and outage-like-pause scenarios inside one fixed-budget benchmark container:

```sh
docker compose --profile bench run --build --rm benchmark --output /results/run --seeds 7,42,2026 --repeats 3 --duration-ms 5000
```

The benchmark runner launches separate producer, collector and sink processes over real loopback TCP within that container. It uses the same program as the demo, but is not a multi-container network-capacity test. Results are retained in the `bench-results` named volume. A nonempty output directory is protected from overwriting. For another run choose a new output name:

```sh
docker compose --profile bench run --rm benchmark --output /results/run-2 --seeds 7,42,2026 --repeats 3 --duration-ms 5000
docker compose --profile bench run --rm --entrypoint cat benchmark /results/run-2/REPORT.md
```

Each run includes `outcomes.csv`, command/config JSON, process logs, sampled producer/collector/sink RSS and CPU time, and final collector metrics. CPU sampling can miss work after the last sample, especially very short runs. The suite produces `REPORT.md`, `FINDINGS.md`, per-run and aggregate JSON, matched-message comparisons and `latency-breakdown.svg`.

## Native Linux / WSL

The executable is `prento` (`build/prento` after a Make build). Only GCC supporting C++20, Make and Python 3 are needed. There are no downloaded C++ libraries or Python packages.

```sh
make test
make sanitize
make bench
```

Alternatively, `cmake -S . -B build-cmake && cmake --build build-cmake && ctest --test-dir build-cmake` builds the binary and core tests. Full process tests use `PRENTO_BINARY=/absolute/path/to/prento python3 -m unittest discover -s tests -p 'test_*.py' -v`.

Change the workload explicitly:

```sh
python3 scripts/bench.py --output results/my-run --seeds 7,42,2026 --repeats 3 --duration-ms 10000 --critical-fraction 0.2 --producers 32
python3 scripts/report.py results/my-run
```

Native runs do **not** apply CPU or memory isolation. Record competing load; use a container budget or dedicated hosts for stronger comparisons. `/proc` sampling is Linux-specific and sampled RSS can miss brief peaks.

## Kubernetes example

[deploy/kubernetes.yaml](../deploy/kubernetes.yaml) supplies two collectors, one bottleneck sink, Services and producer Jobs. Replace image tags with your registry digest (or explicitly load the image into a local cluster), then apply it in an isolated namespace. Job results are on ephemeral pod storage; copy them before deleting pods. This example has no HPA, custom metrics adapter or durability and is **not evidence of multi-node scaling**. Adding collectors cannot scale past the shared sink's capacity.
