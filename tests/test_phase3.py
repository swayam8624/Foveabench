"""FB-CAMPAIGN-01 scientific data, split and policy-leakage regression."""
import csv,tempfile,unittest
from pathlib import Path
from foveabench.phase3 import splits_for,read_data,run

def dataset(path):
    with path.open("w",newline="") as f:
        writer=csv.writer(f)
        writer.writerow(["condition","predictor","trace_id","subject_id","target_ns","has_prediction","angular_error_deg"])
        for s in range(8):
            for model in ("hold","velocity"):
                for t in range(8):
                    writer.writerow(["stress",model,f"trace{s}",f"subject{s}",t*1000000,"True",5 if model=="hold" else 2])

class Phase3Tests(unittest.TestCase):
    def test_seed_locked_disjoint_splits(self):
        a=splits_for([str(i) for i in range(12)],42)
        self.assertEqual(a,splits_for([str(i) for i in range(12)],42))
        self.assertEqual(set(a.values()),{"train","validation","test"})

    def test_real_campaign_and_overwrite_protection(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);source=p/"source.csv";dataset(source)
            rows,models,conditions,subjects,n=read_data(source)
            self.assertEqual(n,128)
            result=run(source,p/"output",seed=42,bootstrap=100)
            self.assertEqual(result["frame_model_rows"],128)
            self.assertFalse(result["rl_agent_trained"])
            self.assertTrue((p/"output/test_uncertainty.csv").exists())
            with self.assertRaises(FileExistsError):run(source,p/"output",bootstrap=100)

    def test_reject_duplicate_input(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/"source.csv";dataset(source)
            with source.open("a") as f:f.write("stress,hold,trace0,subject0,0,True,1\n")
            with self.assertRaises(ValueError):read_data(source)

    def test_test_set_cannot_change_training_selection(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);source=p/"source.csv";dataset(source)
            run(source,p/"before",seed=10,bootstrap=100)
            with (p/"before/splits.csv").open() as f:
                held={r["subject_id"] for r in csv.DictReader(f) if r["split"]=="test"}
            with source.open() as f:rows=list(csv.DictReader(f))
            for row in rows:
                if row["subject_id"] in held and row["predictor"]=="velocity":
                    row["angular_error_deg"]="85"
            altered=p/"altered.csv"
            with altered.open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            run(altered,p/"after",seed=10,bootstrap=100)
            self.assertEqual((p/"before/selected_policies.csv").read_bytes(),
                             (p/"after/selected_policies.csv").read_bytes())
if __name__=="__main__":unittest.main()
