"""Check causal Phase 1 export and strict Phase 2 trace/report contracts.

This is evidence integrity, not a synthetic benchmark score.
"""
import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from foveabench.phase2 import make_trace, export_phase1, analyze, percentile

class Phase2Contract(unittest.TestCase):
    def test_trace_and_no_overwrite(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"trace.csv"
            make_trace(p, 10, 90)
            with p.open() as f:rows=list(csv.DictReader(f))
            self.assertEqual(len(rows),10)
            self.assertLess(int(rows[0]["timestamp_ns"]),int(rows[1]["timestamp_ns"]))
            with self.assertRaises(FileExistsError):make_trace(p)
    def test_phase1_export_pins_selection_and_fallback(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"phase1.csv";out=Path(d)/"trace.csv"
            p.write_text("condition,predictor,trace_id,target_ns,truth_x,truth_y,pred_x,pred_y,has_prediction\n"
                         "latency,hold,a,10000000,.2,.3,.19,.29,True\n"
                         "latency,hold,a,20000000,.3,.4,,,False\n"
                         "latency,hold,b,30000000,.3,.4,.33,.44,True\n")
            with self.assertRaises(ValueError):export_phase1(p,out,"latency","hold","a")
            self.assertFalse(out.exists())  # invalid partial exports must be cleaned up
            self.assertEqual(export_phase1(p,out,"latency","hold","a","hold"),2)
            with out.open() as f:rows=list(csv.DictReader(f))
            self.assertEqual(rows[1]["used_x"],"0.19")
    def test_percentile_endpoints(self):
        self.assertEqual(percentile([1,2,3,4],0),1)
        self.assertEqual(percentile([1,2,3,4],100),4)
        self.assertAlmostEqual(percentile([1,2,3,4],50),2.5)
    def test_analyze_no_fictitious_timestamp(self):
        with TemporaryDirectory() as d:
            p=Path(d)
            (p/"manifest.json").write_text(json.dumps({"suite":"FB-RENDER-01/2.0",
                "results_class":"software-vulkan-functional", "device_name":"example software"}))
            (p/"frames.csv").write_text("scene,policy,device_dispatch_ms,weighted_mse,foveal_mse,sample_fraction_proxy\n"
                                           "chirp,full,,0,0,1\nchirp,full,,0,0,1\n")
            a=analyze(p)
            self.assertFalse(a[0]["device_time_available"])
            self.assertIn("unsupported",(p/"report.md").read_text())
            self.assertFalse(json.loads((p/"manifest.json").read_text())["scientific_qualification"]["hardware_gpu_measured_dispatch"])

if __name__=="__main__":unittest.main()
