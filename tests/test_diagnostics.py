"""A failed process test must retain its files after temporary cleanup."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import test_network as network


class DiagnosticsTest(unittest.TestCase):
    def test_failed_test_retains_process_artifacts(self):
        class FailureProbe(network.NetworkTest):
            def runTest(self):
                (Path(self.tmp.name)/'collector.log').write_text('retained diagnostic\n')
                self.fail('deliberate failure to exercise diagnostic retention')

        with tempfile.TemporaryDirectory() as tmp:
            destination=Path(tmp)/'failures'
            with patch.dict(os.environ,PRENTO_FAILURE_DIR=str(destination)), contextlib.redirect_stderr(io.StringIO()):
                result=unittest.TestResult()
                FailureProbe().run(result)
            self.assertEqual(len(result.failures),1)
            logs=list(destination.glob('*/collector.log'))
            self.assertEqual(len(logs),1)
            self.assertEqual(logs[0].read_text(),'retained diagnostic\n')
