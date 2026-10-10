"""FB-LEARN-RENDER contract checks; native Vulkan exercised by workflow."""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from foveabench.learn_bridge import prepare

class LearnedRenderBridgeTests(unittest.TestCase):
    def make_source(self,base):
        ml=base/"ml";ml.mkdir()
        (ml/"manifest.json").write_text(json.dumps({"suite":"FB-LEARN-01/1.0","synthetic_only":True}))
        (ml/"model.npz").write_bytes(b"synthetic-test-weights")
        source=ml/"test_predictions.csv"
        cols=["condition","trace_id","timestamp_ns","subject_id","truth_x","truth_y",
              "hold_x","hold_y","velocity_x","velocity_y","learned_x","learned_y"]
        with source.open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
            for m in ("fixation","pursuit","jump"):
                for i in range(20):
                    w.writerow(dict(condition="latency-60",trace_id=f"synthetic-{m}-03",
                         timestamp_ns=i*11111111,subject_id=f"test-{m}",truth_x=".50",truth_y=".50",
                         hold_x=".49",hold_y=".49",velocity_x=".51",velocity_y=".51",
                         learned_x=".495",learned_y=".495"))
        return ml
    def test_paired_prepare_and_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);ml=self.make_source(root)
            result=prepare(ml,root/"output","latency-60",12)
            self.assertEqual({m:v["frames"] for m,v in result["trace_counts"].items()},
                             {"fixation":12,"pursuit":12,"jump":12})
            self.assertIn("exploratory",result["data_partition"])
            for m in ("fixation","pursuit","jump"):
                for policy in ("hold","velocity","learned"):
                    rows=list(csv.DictReader((root/"output/traces"/f"{m}-{policy}.csv").open()))
                    self.assertEqual(len(rows),12)
                    self.assertEqual(rows[0]["timestamp_ns"],"0")
            with self.assertRaises(FileExistsError):
                prepare(ml,root/"output","latency-60",12)
    def test_missing_condition_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);ml=self.make_source(root)
            with self.assertRaises(ValueError):
                prepare(ml,root/"missing","unknown-condition",0)

if __name__=="__main__":
    unittest.main()
