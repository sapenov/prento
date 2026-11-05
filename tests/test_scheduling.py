"""Exercise the real TCP collector against a backend with a held first ACK.

The backend controls service completion, not admission or scheduling. Assertions
observe collector grants, byte counters and actual forwarded batch order.
"""
import concurrent.futures
import socket
import struct
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path
import test_network as network

FRAME = struct.Struct("!IBBBBQIIQ")

def exact(sock, count):
    result = b""
    while len(result) < count:
        part = sock.recv(count - len(result))
        if not part:
            raise EOFError("connection closed before full frame")
        result += part
    return result

def payload_header(identity, critical, credit):
    body = bytes([identity]) * 64
    checksum = 2166136261
    for byte in body:
        checksum = ((checksum ^ byte) * 16777619) & 0xFFFFFFFF
    return FRAME.pack(0x46414E31,1,1,critical,credit,identity,64,checksum,0), body

class HeldBackend:
    def __init__(self):
        self.socket = socket.socket()
        self.socket.bind(("127.0.0.1",0))
        self.socket.listen(1)
        self.socket.settimeout(5)
        self.port = self.socket.getsockname()[1]
        self.first = threading.Event()
        self.release = threading.Event()
        self.received = []
        self.error = None
        self.thread = threading.Thread(target=self.serve)
        self.thread.start()

    def serve(self):
        try:
            connection, _ = self.socket.accept()
            with connection:
                connection.settimeout(5)
                for _ in range(3):
                    header = list(FRAME.unpack(exact(connection,32)))
                    exact(connection,header[6])
                    self.received.append(header[5])
                    if header[5] == 1:
                        self.first.set()
                        if not self.release.wait(5):
                            raise TimeoutError("test never released first ACK")
                    header[2] = 3
                    connection.sendall(FRAME.pack(*header))
        except Exception as error:
            self.error = error

    def close(self):
        self.release.set()
        self.thread.join(6)
        self.socket.close()
        if self.thread.is_alive():
            raise AssertionError("controlled backend did not exit")

class SchedulingTest(unittest.TestCase):
    def run_case(self, admission, policy, verify_no_grant=False):
        with tempfile.TemporaryDirectory() as tmp:
            backend = HeldBackend()
            clients = []
            collector = None
            log = open(Path(tmp)/"collector.log","w+")
            try:
                port, metrics = network.port(), network.port()
                collector = subprocess.Popen([
                    str(network.BIN),"collector","--port",str(port),"--metrics-port",str(metrics),
                    "--sink",f"127.0.0.1:{backend.port}","--admission",admission,"--policy",policy,
                    "--buffer-bytes","64","--max-batch-bytes","64","--timeout-ms","4000"
                ],stdout=log,stderr=log)
                network.wait_port(metrics,collector)
                credit = admission == "credit"

                def announce(identity, critical=False):
                    client = socket.create_connection(("127.0.0.1",port),timeout=4)
                    clients.append(client)
                    header,body = payload_header(identity,critical,credit)
                    client.sendall(header)
                    if not credit:
                        client.sendall(body)
                    return client,body

                first,body = announce(1)
                if credit:
                    grant=FRAME.unpack(exact(first,32))
                    self.assertEqual((grant[2],grant[5],grant[6]),(2,1,64))
                    first.sendall(body)
                self.assertTrue(backend.first.wait(3),"first batch never reached backend")

                def state():
                    with urllib.request.urlopen(f"http://127.0.0.1:{metrics}/metrics",timeout=1) as response:
                        return {k:int(v) for k,v in (line.split() for line in response.read().decode().splitlines())}

                def wait_count(count):
                    deadline=time.monotonic()+3
                    while time.monotonic()<deadline:
                        snapshot=state()
                        if snapshot["prento_waiting_announcements"]==count:
                            self.assertEqual(snapshot["prento_reserved_bytes"],64)
                            return
                        time.sleep(.005)
                    self.fail("collector did not expose expected pending announcements")

                bulk,bulk_body=announce(2)
                wait_count(1) # Prove bulk is earlier than the critical announcement.
                critical,critical_body=announce(3,True)
                wait_count(2)
                if verify_no_grant:
                    for client in (bulk,critical):
                        client.settimeout(.1)
                        with self.assertRaises(socket.timeout):
                            client.recv(1)
                        client.settimeout(4)
                    self.assertEqual(state()["prento_reserved_bytes"],64)

                def finish(client,payload):
                    if credit:
                        grant=FRAME.unpack(exact(client,32))
                        self.assertEqual(grant[2],2)
                        client.sendall(payload)
                    ack=FRAME.unpack(exact(client,32))
                    self.assertEqual(ack[2],3)
                    return ack[5]

                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as workers:
                    b=workers.submit(finish,bulk,bulk_body)
                    c=workers.submit(finish,critical,critical_body)
                    backend.release.set()
                    self.assertEqual(FRAME.unpack(exact(first,32))[2],3)
                    self.assertEqual(b.result(4),2)
                    self.assertEqual(c.result(4),3)
                backend.thread.join(2)
                if backend.error:
                    raise backend.error
                expected=[1,3,2] if policy=="priority" else [1,2,3]
                self.assertEqual(backend.received,expected)
                self.assertEqual(state()["prento_reserved_bytes"],0)
            finally:
                backend.release.set()
                for client in clients:
                    client.close()
                if collector:
                    collector.terminate()
                    try: collector.wait(5)
                    except subprocess.TimeoutExpired: collector.kill();collector.wait()
                backend.close()
                log.close()

    def test_later_critical_overtakes_earlier_bulk_in_both_admission_modes(self):
        for admission in ("push","credit"):
            with self.subTest(admission=admission):
                self.run_case(admission,"priority")

    def test_fifo_preserves_order_in_both_admission_modes(self):
        for admission in ("push","credit"):
            with self.subTest(admission=admission):
                self.run_case(admission,"fifo")

    def test_credit_is_withheld_while_full_then_resumes_after_completion(self):
        self.run_case("credit","priority",verify_no_grant=True)
