"""Real-process checks. No mocked collector or transport."""
import csv
import contextlib
import json
import os
from pathlib import Path
import socket
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BIN = Path(os.environ.get("PRENTO_BINARY", ROOT / "build/prento"))

def port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def ports(count):
    chosen = []
    while len(chosen) < count:
        candidate = port()
        if candidate not in chosen:
            chosen.append(candidate)
    return tuple(chosen)

def wait_port(number, process):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(f"service exited: {process.returncode}")
        try:
            with socket.create_connection(("127.0.0.1", number), .1):
                return
        except OSError:
            time.sleep(.02)
    raise AssertionError("service did not start")

class NetworkTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.processes = []

    def tearDown(self):
        for p in reversed(self.processes):
            p.terminate()
        for p in reversed(self.processes):
            try:
                p.wait(4)
            except subprocess.TimeoutExpired:
                p.kill(); p.wait()
            p._log.close()
        result=self._outcome.result
        failures=[trace for case,trace in (*result.failures,*result.errors)
                  if getattr(case,'test_case',case) is self]
        if failures:
            parent=Path(os.environ.get('PRENTO_FAILURE_DIR',ROOT/'qa-local/failures'))
            try:
                parent.mkdir(parents=True,exist_ok=True)
                destination=Path(tempfile.mkdtemp(prefix=self._testMethodName+'-',dir=parent))
                shutil.copytree(self.tmp.name,destination,dirs_exist_ok=True)
                (destination/'FAILURE.txt').write_text('\n'.join(failures))
                print('Failure diagnostics: '+str(destination),file=sys.stderr)
            except OSError as error:
                print('Could not retain test diagnostics: '+str(error),file=sys.stderr)
        self.tmp.cleanup()

    def start(self, *args):
        log = open(Path(self.tmp.name) / f"process-{len(self.processes)}.log", "w+")
        (Path(self.tmp.name)/f'process-{len(self.processes)}.command.json').write_text(json.dumps([str(BIN),*map(str,args)]))
        p = subprocess.Popen([str(BIN), *map(str, args)], stdout=log, stderr=log)
        p._log = log
        self.processes.append(p)
        return p

    def stack(self, admission="push", policy="fifo", **options):
        sink_port, collector_port, metrics_port = ports(3)
        sink = self.start("sink", "--port", sink_port, "--bytes-per-sec", options.get("rate", 1000000),
                          "--outage-start-ms", options.get("outage_start", 0),
                          "--outage-ms", options.get("outage_ms", 0))
        wait_port(sink_port, sink)
        collector = self.start("collector", "--port", collector_port, "--metrics-port", metrics_port,
                               "--sink", f"127.0.0.1:{sink_port}", "--buffer-bytes", 65536,
                               "--max-batch-bytes", 32768, "--timeout-ms", options.get("timeout", 3000),
                               "--admission", admission, "--policy", policy)
        wait_port(metrics_port, collector)
        return sink, collector, collector_port, metrics_port

    def producer(self, target, admission="push", **options):
        output = Path(self.tmp.name) / f"out-{time.monotonic_ns()}.csv"
        cmd = [str(BIN), "producer", "--target", f"127.0.0.1:{target}",
               "--admission", admission, "--duration-ms", str(options.get("duration", 200)),
               "--rate", str(options.get("rate", 100)), "--producers", "4",
               "--bulk-bytes", "4096", "--critical-bytes", "256", "--queue-items", str(options.get("queue", 32)),
               "--timeout-ms", str(options.get("timeout", 3000)), "--output", str(output)]
        output.with_suffix('.command.json').write_text(json.dumps(cmd))
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        except subprocess.TimeoutExpired as error:
            output.with_suffix('.timeout.txt').write_text(str(error))
            for suffix,value in (('.stdout.log',error.stdout),('.stderr.log',error.stderr)):
                output.with_suffix(suffix).write_text(value.decode(errors='replace') if isinstance(value,bytes) else value or '')
            raise
        output.with_suffix('.stdout.log').write_text(r.stdout)
        output.with_suffix('.stderr.log').write_text(r.stderr)
        self.assertEqual(r.returncode, 0, r.stderr)
        with output.open() as f:
            rows = list(csv.DictReader(f))
        return rows

    def test_all_four_modes_complete_and_respect_budget(self):
        for admission in ("push", "credit"):
            for policy in ("fifo", "priority"):
                with self.subTest(admission=admission, policy=policy):
                    _, _, target, metrics = self.stack(admission, policy)
                    rows = self.producer(target, admission)
                    self.assertEqual(len(rows), 20)
                    self.assertEqual(len({r["id"] for r in rows}), 20)
                    self.assertTrue(all(r["status"] == "completed" for r in rows), rows)
                    self.assertTrue(all(float(r["latency_ms"]) >= 0 for r in rows))
                    with urllib.request.urlopen(f"http://127.0.0.1:{metrics}/metrics") as f:
                        values = dict(line.split() for line in f.read().decode().splitlines() if not line.startswith("#"))
                    self.assertLessEqual(int(values["prento_reserved_peak_bytes"]), 65536)
                    self.assertEqual(int(values["prento_reserved_bytes"]), 0)

    def test_reused_port_candidate_keeps_service_endpoints_distinct(self):
        # The OS may return a port again after its probe socket is closed.
        with contextlib.ExitStack() as held:
            candidates = []
            for _ in range(3):
                probe = held.enter_context(socket.socket())
                probe.bind(("127.0.0.1", 0))
                candidates.append(probe.getsockname()[1])
        sink_port, collector_port, metrics_port = candidates
        with patch(__name__ + '.port', side_effect=[sink_port, sink_port, collector_port, metrics_port]):
            _, _, target, metrics = self.stack()
        self.assertEqual(target, collector_port)
        self.assertEqual(metrics, metrics_port)
        with socket.create_connection(("127.0.0.1", target), timeout=1):
            pass
        with urllib.request.urlopen(f"http://127.0.0.1:{metrics}/metrics", timeout=1) as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b'prento_buffer_limit_bytes 65536', response.read())

    def test_sink_loss_produces_explicit_unknown_outcomes(self):
        sink, _, target, _ = self.stack(timeout=300)
        sink.terminate(); sink.wait(2)
        rows = self.producer(target, timeout=500, duration=100)
        self.assertEqual(len(rows), 10)
        self.assertTrue(all(r["status"] == "failed_unknown" for r in rows), rows)

    def test_overload_accounts_for_every_generated_item(self):
        _, _, target, _ = self.stack(rate=10000, timeout=2000)
        rows = self.producer(target, duration=100, rate=1000, queue=1, timeout=2000)
        self.assertEqual(len(rows), 100)
        self.assertEqual(len({r["id"] for r in rows}), 100)
        self.assertTrue(any(r["status"] == "producer_drop" for r in rows))

    def test_oversized_header_is_rejected_without_body(self):
        _, _, target, _ = self.stack()
        # magic, version, ANNOUNCE, critical, credit-mode, id, bytes, checksum, intended-ns
        header = struct.pack("!IBBBBQIIQ", 0x46414E31, 1, 1, 0, 0, 99, 99999999, 0, 0)
        with socket.create_connection(("127.0.0.1", target), timeout=1) as s:
            s.sendall(header)
            reply = s.recv(32)
            self.assertEqual(len(reply), 32)
            self.assertEqual(reply[5], 4)

    def test_corrupt_body_never_gets_success_ack(self):
        _, _, target, _ = self.stack()
        header = struct.pack("!IBBBBQIIQ", 0x46414E31, 1, 1, 0, 0, 99, 3, 0, 0)
        with socket.create_connection(("127.0.0.1", target), timeout=1) as s:
            s.sendall(header + b"abc")
            reply = s.recv(32)
            self.assertTrue(not reply or reply[5] == 4)

    def test_invalid_options_fail(self):
        for args in (("collector", "--buffer-bytes", "0"),
                     ("producer", "--rate", "0"),
                     ("collector", "--policy", "mystery"),
                     ("producer", "--seed", "not-a-number"),
                     ("sink", "--bytes-per-secc", "100")):
            command = [str(BIN), *args]
            if args[0] == "producer":
                command += ["--output", str(Path(self.tmp.name) / "invalid.csv")]
            r = subprocess.run(command, capture_output=True, timeout=3)
            self.assertNotEqual(r.returncode, 0)
            self.assertGreater(r.returncode, 0, "invalid input must fail cleanly, not abort")

    def test_producer_termination_interrupts_scheduled_wait(self):
        p = self.start("producer", "--start-delay-ms", 10000, "--duration-ms", 1,
                       "--producers", 1, "--output", Path(self.tmp.name) / "stopped.csv")
        time.sleep(.1)
        p.terminate()
        p.wait(timeout=1)
        self.assertEqual(p.returncode, 0)

    def test_stalled_body_releases_reservation(self):
        _, _, target, metrics = self.stack(timeout=200)
        header = struct.pack("!IBBBBQIIQ", 0x46414E31, 1, 1, 0, 0, 99, 32768, 0, 0)
        with socket.create_connection(("127.0.0.1", target), timeout=1) as s:
            s.sendall(header + b"partial")
            time.sleep(.4)
        with urllib.request.urlopen(f"http://127.0.0.1:{metrics}/metrics") as f:
            values = dict(line.split() for line in f.read().decode().splitlines())
        self.assertEqual(int(values["prento_reserved_bytes"]), 0)

    def test_idle_sink_connection_can_be_reused(self):
        _, _, target, _ = self.stack()
        rows = self.producer(target, duration=100)
        self.assertTrue(all(r["status"] == "completed" for r in rows))
        time.sleep(1.2)
        rows = self.producer(target, duration=100)
        self.assertTrue(all(r["status"] == "completed" for r in rows), rows)

    def test_low_rate_producers_keep_idle_connections(self):
        _, _, target, _ = self.stack(timeout=200)
        rows = self.producer(target, duration=1000, rate=8, timeout=200)
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(r["status"] == "completed" for r in rows), rows)

if __name__ == "__main__":
    unittest.main()
