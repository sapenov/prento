"""Candidate test: priority among batches that are already admitted and ready.

The existing scheduling test fills a one-batch budget, so it exercises the
admission selector only. Here the budget admits all three batches; while the
backend holds the first ACK, batches 2 (bulk) and 3 (critical) wait in the
collector's ready list, so the order the backend receives depends only on the
service selector.
"""
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, os.environ.get("PRENTO_TESTS", str(Path(__file__).resolve().parent)))
import test_network as network  # noqa: E402
from test_scheduling import FRAME, HeldBackend, exact, payload_header  # noqa: E402


class ServicePriorityTest(unittest.TestCase):
    def run_case(self, admission, policy):
        backend = HeldBackend()
        clients, collector = [], None
        with tempfile.TemporaryDirectory() as tmp:
            log = open(Path(tmp) / "collector.log", "w+")
            try:
                port, metrics = network.ports(2)
                collector = subprocess.Popen(
                    [str(network.BIN), "collector", "--port", str(port), "--metrics-port", str(metrics),
                     "--sink", f"127.0.0.1:{backend.port}", "--admission", admission, "--policy", policy,
                     "--buffer-bytes", "192", "--max-batch-bytes", "64", "--timeout-ms", "4000"],
                    stdout=log, stderr=log)
                network.wait_port(metrics, collector)
                credit = admission == "credit"

                def state():
                    with urllib.request.urlopen(f"http://127.0.0.1:{metrics}/metrics", timeout=1) as r:
                        return {k: int(v) for k, v in (line.split() for line in r.read().decode().splitlines())}

                def wait_ready(count):
                    deadline = time.monotonic() + 3
                    while time.monotonic() < deadline:
                        if state()["prento_ready_batches"] == count:
                            return
                        time.sleep(.005)
                    self.fail(f"expected {count} ready batches")

                def send(identity, critical=False):
                    client = socket.create_connection(("127.0.0.1", port), timeout=4)
                    clients.append(client)
                    header, body = payload_header(identity, critical, credit)
                    client.sendall(header)
                    if credit:  # budget has room, so the grant is immediate
                        self.assertEqual(FRAME.unpack(exact(client, 32))[2], 2)
                    client.sendall(body)
                    return client

                first = send(1)
                self.assertTrue(backend.first.wait(3), "first batch never reached backend")
                bulk = send(2)
                wait_ready(1)            # bulk is admitted and ready before the critical batch exists
                critical = send(3, True)
                wait_ready(2)
                self.assertEqual(state()["prento_waiting_announcements"], 0)  # no admission contention
                backend.release.set()
                for client in (first, bulk, critical):
                    self.assertEqual(FRAME.unpack(exact(client, 32))[2], 3)
                backend.thread.join(2)
                if backend.error:
                    raise backend.error
                self.assertEqual(backend.received, [1, 3, 2] if policy == "priority" else [1, 2, 3])
            finally:
                backend.release.set()
                for client in clients:
                    client.close()
                if collector:
                    collector.terminate()
                    try:
                        collector.wait(5)
                    except subprocess.TimeoutExpired:
                        collector.kill(); collector.wait()
                backend.close()
                log.close()

    def test_ready_critical_overtakes_ready_bulk(self):
        for admission in ("push", "credit"):
            with self.subTest(admission=admission):
                self.run_case(admission, "priority")

    def test_ready_fifo_preserves_order(self):
        for admission in ("push", "credit"):
            with self.subTest(admission=admission):
                self.run_case(admission, "fifo")


if __name__ == "__main__":
    unittest.main()
