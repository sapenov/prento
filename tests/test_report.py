"""Literal outcomes prove loss accounting and intended-time percentiles."""
import importlib.util
import copy
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ReportTest(unittest.TestCase):
    def test_report_includes_losses_and_uses_nearest_rank(self):
        path = ROOT / "scripts/report.py"
        self.assertTrue(path.exists(), "report implementation is missing")
        spec = importlib.util.spec_from_file_location("prento_report", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        rows = [
            {"id":"1","class":"critical","bytes":"100","intended_ns":"1000000000", "send_ns":"1002000000", "end_ns":"1010000000","latency_ms":"10", "producer_wait_ms":"2","status":"completed"},
            {"id":"2","class":"critical","bytes":"100","intended_ns":"1010000000", "send_ns":"1015000000", "end_ns":"1040000000","latency_ms":"30", "producer_wait_ms":"5","status":"completed"},
            {"id":"3","class":"critical","bytes":"100","intended_ns":"1020000000", "end_ns":"1020000001","latency_ms":"0.000001", "producer_wait_ms":"0","status":"producer_drop"},
            {"id":"4","class":"bulk","bytes":"1000","intended_ns":"1030000000", "end_ns":"2000000000","latency_ms":"970", "producer_wait_ms":"20","status":"failed_unknown"},
        ]
        result = module.summarize(rows, 100)
        self.assertEqual(result["generated"], 4)
        self.assertEqual(result["completed"], 2)
        self.assertEqual(result["generated_bytes"], 1300)
        self.assertEqual(result["completed_bytes"], 200)
        self.assertEqual(result["failed_unknown_bytes"], 1000)
        self.assertEqual(result["producer_drop_bytes"], 100)
        self.assertEqual(result["classes"]["critical"]["p99_ms"], 30)
        self.assertEqual(result["classes"]["critical"]["mean_pre_send_ms"], 3.5)
        self.assertEqual(result["classes"]["critical"]["mean_post_send_ms"], 16.5)
        self.assertEqual(result["classes"]["critical"]["max_ms"], 30)
        self.assertTrue(result["classes"]["critical"]["p99_equals_max"])
        self.assertAlmostEqual(result["classes"]["critical"]["completion_fraction"], 2/3)
        with self.assertRaises(ValueError):
            module.summarize(rows + [rows[0]], 100)

    def test_paired_comparison_validates_inputs_and_preserves_failures(self):
        spec = importlib.util.spec_from_file_location("prento_report", ROOT / "scripts/report.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        reference = [
            {"id":"1","producer":"0","class":"critical","bytes":"100","intended_ns":"1000000000","send_ns":"1002000000","end_ns":"1010000000","status":"completed"},
            {"id":"2","producer":"0","class":"critical","bytes":"100","intended_ns":"1010000000","send_ns":"1015000000","end_ns":"1040000000","status":"completed"},
        ]
        candidate = [dict(reference[0],end_ns="1006000000"),dict(reference[1],send_ns="1020000000",end_ns="1030000000")]
        result = module.compare_pair(reference,candidate)
        self.assertEqual(result["classes"]["critical"]["both_completed"], 2)
        self.assertEqual(result["classes"]["critical"]["faster"], 2)
        self.assertEqual(result["classes"]["critical"]["mean_reduction_pct"], 35)
        candidate[1]["status"] = "failed_unknown"
        result = module.compare_pair(reference,candidate)
        self.assertEqual(result["classes"]["critical"]["both_completed"], 1)
        self.assertEqual(result["classes"]["critical"]["reference_only_completed"], 1)
        candidate[1]["bytes"] = "101"
        with self.assertRaises(ValueError):
            module.compare_pair(reference,candidate)

    def test_impossible_completed_timestamps_are_rejected(self):
        spec = importlib.util.spec_from_file_location("prento_report", ROOT / "scripts/report.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        row={"id":"1","class":"critical","bytes":"100","intended_ns":"100","send_ns":"0","end_ns":"200","latency_ms":"0.0001","producer_wait_ms":"0","status":"completed"}
        with self.assertRaises(ValueError):
            module.summarize([row], 100)

    def test_matching_modes_require_same_experiment_and_binary(self):
        spec = importlib.util.spec_from_file_location("prento_report", ROOT / "scripts/report.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        common=dict(duration_ms=1000,rate=100,sink_rate=1000000,producers=4,queue_items=16,
                    buffer_bytes=65536,bulk_bytes=4096,critical_bytes=256,critical_fraction=.05,
                    timeout_ms=3000,seed=7,scenario='burst',binary_sha256='a'*64)
        configs=[dict(common,admission=a,policy=p) for a in ('push','credit') for p in ('fifo','priority')]
        self.assertEqual(module.validate_group(configs)['binary_identity_source'],'per-run')
        for key,value in [('sink_rate',2000000),('buffer_bytes',32768),('binary_sha256','b'*64)]:
            changed=copy.deepcopy(configs);changed[-1][key]=value
            with self.assertRaises(ValueError):module.validate_group(changed)
        legacy=[{k:v for k,v in c.items() if k!='binary_sha256'} for c in configs]
        self.assertEqual(module.validate_group(legacy,'a'*64)['binary_identity_source'],'global-environment')

if __name__ == "__main__":
    unittest.main()
