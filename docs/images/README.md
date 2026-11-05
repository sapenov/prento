# README results figure

`results.svg` is the vector image embedded in the main README. `results.png` provides a raster copy for export or sharing. Both show mean critical end-to-end latency for push/FIFO and push/priority in the burst and slow-sink scenarios.

Source: [aggregate.json](../../results/2026-11-04-qa/aggregate.json) and [summary.json](../../results/2026-11-04-qa/summary.json). The renderer checks the published aggregate against equally weighted run means, then computes reductions and descriptive per-seed ranges. Each bar represents nine runs over three seeds. See [all scenarios and trade-offs](../../results/2026-11-04-qa/INTERPRETATION.md).

To regenerate from the repository root:

```sh
python3 docs/images/render_results.py
```

Matplotlib is needed only to author these documentation images. Application builds, benchmark execution and tests have no new dependencies. The renderer writes only these two images; source benchmark evidence is read-only.
