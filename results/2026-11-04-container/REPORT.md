# Measured fan-in results

These are local workload observations, not production capacity claims.

Latency includes producer waiting and sink processing. Percentiles include completed messages only; completion and failure counts must be read alongside them.

A p99 based on a small sample is effectively near the maximum; do not infer stable tails from short runs. Repeats measure timing variation with the same synthetic workload seed.

| Scenario | Mode | Run | Critical n / generated | Critical p99 ms | Bulk p99 ms | Drops | Unknown | Collector peak RSS KiB |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| burst | credit/fifo | 1 | 18/18 | 1108.20 | 1093.74 | 0 | 0 | 5068 |
| burst | credit/fifo | 2 | 18/18 | 1125.12 | 1114.08 | 0 | 0 | 4984 |
| burst | credit/fifo | 3 | 18/18 | 1102.06 | 1083.53 | 0 | 0 | 5012 |
| burst | credit/priority | 1 | 18/18 | 1032.72 | 1177.93 | 0 | 0 | 5000 |
| burst | credit/priority | 2 | 18/18 | 988.20 | 1114.34 | 0 | 0 | 5000 |
| burst | credit/priority | 3 | 18/18 | 1007.89 | 1130.56 | 0 | 0 | 5024 |
| burst | push/fifo | 1 | 18/18 | 1080.14 | 1064.27 | 0 | 0 | 5112 |
| burst | push/fifo | 2 | 18/18 | 1082.73 | 1067.87 | 0 | 0 | 5132 |
| burst | push/fifo | 3 | 18/18 | 1102.73 | 1090.52 | 0 | 0 | 5048 |
| burst | push/priority | 1 | 18/18 | 1030.92 | 1156.14 | 0 | 0 | 5072 |
| burst | push/priority | 2 | 18/18 | 1007.32 | 1133.12 | 0 | 0 | 5024 |
| burst | push/priority | 3 | 18/18 | 1030.57 | 1169.78 | 0 | 0 | 5024 |
| outage | credit/fifo | 1 | 13/13 | 897.67 | 895.81 | 0 | 0 | 5028 |
| outage | credit/fifo | 2 | 13/13 | 898.69 | 897.29 | 0 | 0 | 5020 |
| outage | credit/fifo | 3 | 13/13 | 896.75 | 895.44 | 0 | 0 | 4996 |
| outage | credit/priority | 1 | 13/13 | 898.14 | 898.13 | 0 | 0 | 4992 |
| outage | credit/priority | 2 | 13/13 | 898.79 | 900.12 | 0 | 0 | 4952 |
| outage | credit/priority | 3 | 13/13 | 897.10 | 897.79 | 0 | 0 | 5020 |
| outage | push/fifo | 1 | 13/13 | 897.62 | 895.81 | 0 | 0 | 4976 |
| outage | push/fifo | 2 | 13/13 | 897.50 | 896.31 | 0 | 0 | 4996 |
| outage | push/fifo | 3 | 13/13 | 899.31 | 896.61 | 0 | 0 | 4936 |
| outage | push/priority | 1 | 13/13 | 899.24 | 899.46 | 0 | 0 | 5016 |
| outage | push/priority | 2 | 13/13 | 898.05 | 898.62 | 0 | 0 | 4988 |
| outage | push/priority | 3 | 13/13 | 898.00 | 898.41 | 0 | 0 | 5020 |
| slow | credit/fifo | 1 | 13/13 | 814.27 | 836.32 | 0 | 0 | 4960 |
| slow | credit/fifo | 2 | 13/13 | 811.59 | 837.42 | 0 | 0 | 5012 |
| slow | credit/fifo | 3 | 13/13 | 760.09 | 776.40 | 0 | 0 | 5076 |
| slow | credit/priority | 1 | 13/13 | 691.99 | 842.79 | 0 | 0 | 5032 |
| slow | credit/priority | 2 | 13/13 | 696.49 | 848.72 | 0 | 0 | 5028 |
| slow | credit/priority | 3 | 13/13 | 693.72 | 845.16 | 0 | 0 | 5108 |
| slow | push/fifo | 1 | 13/13 | 759.91 | 774.53 | 0 | 0 | 5036 |
| slow | push/fifo | 2 | 13/13 | 772.43 | 784.66 | 0 | 0 | 5128 |
| slow | push/fifo | 3 | 13/13 | 812.04 | 836.25 | 0 | 0 | 5024 |
| slow | push/priority | 1 | 13/13 | 685.33 | 845.47 | 0 | 0 | 5000 |
| slow | push/priority | 2 | 13/13 | 685.95 | 846.68 | 0 | 0 | 5020 |
| slow | push/priority | 3 | 13/13 | 686.45 | 845.90 | 0 | 0 | 5096 |
| steady | credit/fifo | 1 | 13/13 | 2.10 | 10.57 | 0 | 0 | 4976 |
| steady | credit/fifo | 2 | 13/13 | 2.46 | 10.96 | 0 | 0 | 4988 |
| steady | credit/fifo | 3 | 13/13 | 2.30 | 10.50 | 0 | 0 | 5020 |
| steady | credit/priority | 1 | 13/13 | 2.13 | 10.25 | 0 | 0 | 5004 |
| steady | credit/priority | 2 | 13/13 | 2.30 | 10.24 | 0 | 0 | 4628 |
| steady | credit/priority | 3 | 13/13 | 2.01 | 10.10 | 0 | 0 | 4952 |
| steady | push/fifo | 1 | 13/13 | 2.08 | 10.72 | 0 | 0 | 4988 |
| steady | push/fifo | 2 | 13/13 | 2.21 | 10.45 | 0 | 0 | 4740 |
| steady | push/fifo | 3 | 13/13 | 1.89 | 10.22 | 0 | 0 | 4652 |
| steady | push/priority | 1 | 13/13 | 1.94 | 10.09 | 0 | 0 | 5096 |
| steady | push/priority | 2 | 13/13 | 2.18 | 10.21 | 0 | 0 | 4640 |
| steady | push/priority | 3 | 13/13 | 1.85 | 10.30 | 0 | 0 | 4572 |

## Interpretation

Compare push/FIFO with push/priority to isolate priority; push/FIFO with credit/FIFO to isolate credits; and push/priority with credit/priority for the incremental value of credits.

The collector bounds reserved payload bytes. This is not a process-RSS cap: threads, metadata, producer payloads and kernel socket buffers require additional memory. Producer peak queued bytes are logical synthetic payload sizes; payloads are materialized at send time.

failed_unknown means processing may have occurred but the final ACK was not observed. There is no automatic replay or durable exactly-once guarantee.
