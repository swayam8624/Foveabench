"""Frozen-checkpoint transfer: subject-exclusion and checkpoint integrity checks."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from argparse import Namespace
from contextlib import redirect_stdout
import io

import numpy as np

from foveabench.learn_transfer import checkpoint,evaluate,inspection

class FrozenEvaluationTests(unittest.TestCase):
    def fixture(self,d):
        p=Path(d)
        source=p/"trained";source.mkdir()
        (source/"manifest.json").write_text(json.dumps({"suite":"FB-LEARN-01/1.0","sha256_input":"training-hash","best_epoch":7}))
        with (source/"splits.csv").open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=["subject_id","split"]);w.writeheader()
            w.writerow({"subject_id":"synthetic-agent-fixation-00","split":"train"})
        np.savez_compressed(source/"model.npz",
            w1=np.zeros((9,2)),b1=np.zeros(2),w2=np.zeros((2,1)),b2=np.zeros(1),
            mean=np.zeros(9),std=np.ones(9),
            features=np.array(["hold_x","hold_y","velocity_dx","velocity_dy","disagreement",
                               "age_100ms","sample_count_10","past_hold_dx_10","past_hold_dy_10"]))
        return source
    def test_checkpoint_schema(self):
        with tempfile.TemporaryDirectory() as d:
            source=self.fixture(d)
            *_,manifest,path=checkpoint(source)
            self.assertEqual(manifest["best_epoch"],7)
            self.assertTrue(path.exists())
    def write_predictions(self, source, weight_column, value="0.25", count=8):
        path=source/"test_predictions.csv"
        columns=["condition","trace_id","subject_id",weight_column]
        with path.open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=columns);w.writeheader()
            for i in range(count):
                w.writerow({"condition":"clean","trace_id":"synthetic-pursuit-03",
                            "subject_id":"synthetic-agent-pursuit-03",
                            weight_column:value})
        return path
    def test_inspect_original_training_output_blend_weight(self):
        with tempfile.TemporaryDirectory() as d:
            source=self.fixture(d)
            self.write_predictions(source,"blend_weight",value="0.25")
            with redirect_stdout(io.StringIO()) as text:
                rows=inspection(Namespace(ml_output=source))
            self.assertEqual(len(rows["ALL"]),8)
            self.assertAlmostEqual(sum(rows["ALL"])/8,.25)
            self.assertIn("blend_weight",text.getvalue())
    def test_inspect_transfer_output_velocity_weight(self):
        with tempfile.TemporaryDirectory() as d:
            source=self.fixture(d)
            self.write_predictions(source,"velocity_weight",value="0.8")
            with redirect_stdout(io.StringIO()) as text:
                rows=inspection(Namespace(ml_output=source))
            self.assertAlmostEqual(sum(rows["ALL"])/8,.8)
            self.assertIn("velocity_weight",text.getvalue())
    def test_inspect_rejects_missing_or_invalid_weight(self):
        with tempfile.TemporaryDirectory() as d:
            source=self.fixture(d)
            self.write_predictions(source,"unknown_weight",value="0.3")
            with self.assertRaisesRegex(ValueError,"Missing blend_weight"):
                inspection(Namespace(ml_output=source))
            self.write_predictions(source,"blend_weight",value="nan")
            with self.assertRaisesRegex(ValueError,"Invalid policy blending weight"):
                inspection(Namespace(ml_output=source))
            self.write_predictions(source,"blend_weight",value="0.0",count=0)
            with self.assertRaisesRegex(ValueError,"Empty learned prediction audit"):
                inspection(Namespace(ml_output=source))
    def test_reject_no_fresh_id(self):
        with tempfile.TemporaryDirectory() as d:
            from argparse import Namespace
            source=self.fixture(d)
            f=Path(d)/"frames.csv"
            cols=["condition","predictor","trace_id","subject_id","target_ns",
                  "truth_x","truth_y","pred_x","pred_y","has_prediction","age_ms","delivered_samples"]
            with f.open("w",newline="") as fd:
                w=csv.DictWriter(fd,fieldnames=cols);w.writeheader()
                for i in range(150):
                    for m in ("hold","velocity"):
                        w.writerow({"condition":"clean","predictor":m,"trace_id":"synthetic-fixation-00",
                                    "subject_id":"synthetic-agent-fixation-00","target_ns":i*11111111,
                                    "truth_x":".5","truth_y":".5","pred_x":".5","pred_y":".5",
                                    "has_prediction":"True","age_ms":"0","delivered_samples":"1"})
            with self.assertRaisesRegex(ValueError,"No genuinely unused"):
                evaluate(Namespace(ml_output=source,phase1_frames=f,output=Path(d)/"run",allow_seen=False))
if __name__=="__main__":
    unittest.main()
