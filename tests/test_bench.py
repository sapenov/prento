"""Schedule construction must cover every seed/mode independently of ordering."""
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("prento_bench",ROOT/"scripts/bench.py")
bench=importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)

class BenchTest(unittest.TestCase):
    def test_seed_parser_rejects_ambiguous_and_invalid_inputs(self):
        self.assertEqual(bench.parse_seeds("7,42,2026",42),[7,42,2026])
        self.assertEqual(bench.parse_seeds(None,42),[42])
        for value in ("7,7","-1","","7,",str(2**64)):
            with self.assertRaises(ValueError):bench.parse_seeds(value,42)

    def test_schedule_covers_each_combination_and_repeats_order(self):
        a=bench.work_items(["steady","burst"],[7,42],2,99)
        b=bench.work_items(["steady","burst"],[7,42],2,99)
        self.assertEqual(a,b)
        self.assertEqual(len(a),32)
        self.assertEqual(len(set(a)),32)
        expected={(s,a,p,seed,r) for s in ("steady","burst") for a in ("push","credit")
                  for p in ("fifo","priority") for seed in (7,42) for r in (1,2)}
        self.assertEqual(set(a),expected)
