#!/usr/bin/env python3
"""Orchestrate native TCP services. Linux /proc sampling; Python stdlib only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from report import render

def unused_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def wait_ready(port, process):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("service exited before readiness; inspect service log")
        try:
            with socket.create_connection(("127.0.0.1", port), .1):
                return
        except OSError:
            time.sleep(.02)
    raise RuntimeError("readiness timeout")

def rss(pid):
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except FileNotFoundError:
        pass
    return 0

def cpu_seconds(pid):
    try:
        text = Path(f"/proc/{pid}/stat").read_text()
        fields = text[text.rfind(")") + 2:].split()
        return (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK")
    except (OSError, ValueError, IndexError):
        return 0

def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(8)
    except subprocess.TimeoutExpired:
        process.kill(); process.wait()

def parse_seeds(text, fallback):
    try:
        seeds = [int(value) for value in text.split(",")] if text is not None else [fallback]
    except ValueError as error:
        raise ValueError("seeds must be comma-separated unsigned integers") from error
    if not seeds or len(set(seeds)) != len(seeds) or any(value < 0 or value >= 2**64 for value in seeds):
        raise ValueError("seeds must be unique unsigned 64-bit integers")
    return seeds

def work_items(scenarios, seeds, repeats, order_seed):
    jobs = [(s,a,p,seed,r) for s in scenarios for a in ("push","credit")
            for p in ("fifo","priority") for seed in seeds for r in range(1,repeats+1)]
    random.Random(order_seed).shuffle(jobs)
    return jobs

def run(args, scenario, admission, policy, seed, repeat, destination):
    folder = destination / f"{scenario}-seed-{seed}-{admission}-{policy}-{repeat}"
    folder.mkdir()
    ports = []
    while len(ports) < 3:
        candidate = unused_port()
        if candidate not in ports:
            ports.append(candidate)
    sinkport, collectorport, metricsport = ports
    binary = str(Path(args.binary).resolve())
    sinkcmd = [binary, "sink", "--port", str(sinkport), "--bytes-per-sec", str(args.sink_rate)]
    if scenario == "slow":
        sinkcmd += ["--slow-start-ms", str(args.duration_ms * .3), "--slow-ms", str(args.duration_ms * .3), "--slow-factor", "10"]
    if scenario == "outage":
        sinkcmd += ["--outage-start-ms", str(args.duration_ms * .3), "--outage-ms", str(args.duration_ms * .3)]
    collectorcmd = [binary, "collector", "--port", str(collectorport), "--metrics-port", str(metricsport),
                    "--sink", f"127.0.0.1:{sinkport}", "--admission", admission, "--policy", policy,
                    "--buffer-bytes", str(args.buffer_bytes), "--max-batch-bytes", str(max(args.bulk_bytes, args.critical_bytes)),
                    "--timeout-ms", str(args.timeout_ms)]
    producercmd = [binary, "producer", "--target", f"127.0.0.1:{collectorport}", "--admission", admission,
                   "--duration-ms", str(args.duration_ms), "--rate", str(args.rate), "--producers", str(args.producers),
                   "--bulk-bytes", str(args.bulk_bytes), "--critical-bytes", str(args.critical_bytes),
                   "--critical-fraction", str(args.critical_fraction), "--queue-items", str(args.queue_items),
                   "--timeout-ms", str(args.timeout_ms), "--seed", str(seed), "--output", str(folder / "outcomes.csv")]
    if scenario == "burst":
        producercmd += ["--burst-factor", "3"]
    processes, logs = [], []
    measurements = {"collector_peak_rss_kib": 0, "producer_peak_rss_kib": 0, "sink_peak_rss_kib": 0}
    started = time.monotonic()
    try:
        for name, command, port in (("sink", sinkcmd, sinkport), ("collector", collectorcmd, metricsport)):
            log = (folder / f"{name}.log").open("w")
            logs.append(log)
            process = subprocess.Popen(command, stdout=log, stderr=log)
            processes.append(process)
            wait_ready(port, process)
        producerlog = (folder / "producer.log").open("w")
        logs.append(producerlog)
        producer = subprocess.Popen(producercmd, stdout=producerlog, stderr=producerlog)
        processes.append(producer)
        limit = time.monotonic() + args.duration_ms / 1000 + args.drain_timeout
        while producer.poll() is None:
            for name, process in zip(("sink", "collector", "producer"), processes):
                key = f"{name}_peak_rss_kib"
                measurements[key] = max(measurements[key], rss(process.pid))
                cpu_key = f"{name}_sampled_cpu_seconds"
                measurements[cpu_key] = max(measurements.get(cpu_key, 0), cpu_seconds(process.pid))
            if time.monotonic() > limit:
                raise RuntimeError("producer drain deadline exceeded; partial results preserved")
            time.sleep(.02)
        if producer.returncode:
            raise RuntimeError("producer failed; inspect producer.log")
        with urllib.request.urlopen(f"http://127.0.0.1:{metricsport}/metrics", timeout=2) as response:
            metrics = response.read().decode()
        (folder / "collector.prom").write_text(metrics)
        measurements["collector_final_counters"] = {
            line.split()[0]: int(line.split()[1]) for line in metrics.splitlines()
        }
    finally:
        for p in reversed(processes):
            stop(p)
        for log in logs:
            log.close()
    producer_summary = json.loads((folder / "producer.log").read_text().strip().splitlines()[-1])
    config = {**vars(args), "seed": seed, "order_seed": args.seed, "scenario": scenario, "admission": admission, "policy": policy, "repeat": repeat,
              "measurements": measurements, "producer_summary": producer_summary,
              "elapsed_seconds": time.monotonic() - started,
              "commands": {"sink": sinkcmd, "collector": collectorcmd, "producer": producercmd}}
    (folder / "run.json").write_text(json.dumps(config, indent=2) + "\n")
    print(f"{folder.name}: generated={producer_summary['generated']} completed={producer_summary['completed']} drops={producer_summary['producer_drop']} unknown={producer_summary['failed_unknown']}", flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", default=str(ROOT / "build/prento"))
    parser.add_argument("--output", default="results/latest")
    parser.add_argument("--duration-ms", type=int, default=3000)
    parser.add_argument("--rate", type=float, default=100)
    parser.add_argument("--sink-rate", type=float, default=4194304)
    parser.add_argument("--producers", type=int, default=16)
    parser.add_argument("--queue-items", type=int, default=16)
    parser.add_argument("--buffer-bytes", type=int, default=262144)
    parser.add_argument("--bulk-bytes", type=int, default=32768)
    parser.add_argument("--critical-bytes", type=int, default=256)
    parser.add_argument("--critical-fraction", type=float, default=.05)
    parser.add_argument("--timeout-ms", type=int, default=5000)
    parser.add_argument("--drain-timeout", type=float, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--seeds", help="Comma-separated workload seeds; --seed also determines run order")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--scenarios", default="steady,burst,slow,outage")
    args = parser.parse_args()
    try:
        seeds = parse_seeds(args.seeds,args.seed)
    except ValueError as error:
        parser.error(str(error))
    if args.repeats < 1 or args.duration_ms < 1 or args.drain_timeout <= 0:
        parser.error("positive repeats, duration and drain-timeout required")
    scenarios = args.scenarios.split(",")
    if not scenarios or any(s not in ("steady", "burst", "slow", "outage") for s in scenarios):
        parser.error("unknown scenario")
    destination = Path(args.output).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise SystemExit("output directory is nonempty; select a new path to preserve evidence")
    destination.mkdir(parents=True, exist_ok=True)
    environment = {"platform": platform.platform(), "cpu_count": os.cpu_count(),
                   "python": sys.version, "argv": sys.argv, "cpu_model": "unknown",
                   "binary_sha256": hashlib.sha256(Path(args.binary).read_bytes()).hexdigest()}
    args.binary_sha256=environment['binary_sha256']
    for key, path in (("cgroup_cpu_max", "/sys/fs/cgroup/cpu.max"),
                      ("cgroup_memory_max", "/sys/fs/cgroup/memory.max")):
        try:
            environment[key] = Path(path).read_text().strip()
        except OSError:
            environment[key] = "unavailable"
    try:
        environment["cpu_model"] = next(line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines() if line.startswith("model name"))
    except (OSError, StopIteration):
        pass
    (destination / "environment.json").write_text(json.dumps(environment, indent=2) + "\n")
    jobs = work_items(scenarios,seeds,args.repeats,args.seed)
    for scenario, admission, policy, seed, repeat in jobs:
        run(args, scenario, admission, policy, seed, repeat, destination)
    render(destination)
    print("report:", destination / "REPORT.md")

if __name__ == "__main__":
    main()
