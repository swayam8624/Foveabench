"""Paper verification never fakes human data or accepts invalid study labels."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from foveabench.paper_validation import read_register,spearman,preference_agreement,compare


class PaperValidationTests(unittest.TestCase):
    def test_registry_contracts(self):
        m=read_register()
        self.assertGreaterEqual(len(m["papers"]),4)
        self.assertTrue(all(p["state"]!="reproduced" for p in m["papers"]))

    def test_spearman_ties_and_pairwise_preferences(self):
        self.assertAlmostEqual(spearman([1,2,3,4],[10,20,30,40]),1.0)
        self.assertAlmostEqual(spearman([1,2,3,4],[40,30,20,10]),-1.0)
        self.assertTrue(0<preference_agreement([1,2,3,4],[1,3,2,4])[0]<1)

    def test_cannot_pass_synthetic_labels_as_humans(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);source=p/"ratings.csv";provenance=p/"provenance.json"
            with source.open("w",newline="") as f:
                w=csv.writer(f);w.writerow(["participant_id","stimulus_id","human_score","predicted_score"])
                for i in range(5):
                    for j in range(6):w.writerow([str(i),str(j),j+i*.1,j])
            fields={"paper_id":"SIGGRAPH-2021-FOVVIDEOVDP","source_url":"https://example.org",
                "license":"unknown","human_rating_source":"synthetic","display_calibration":"unverified",
                "quality_higher_is_better":True,"provenance_verified_by_operator":True}
            provenance.write_text(json.dumps(fields))
            with self.assertRaisesRegex(ValueError,"simulated ratings"):
                compare(source,provenance,p/"out",30,1)
            fields["human_rating_source"]="claimed-published"
            fields["provenance_verified_by_operator"]=False
            provenance.write_text(json.dumps(fields))
            with self.assertRaisesRegex(ValueError,"Operator must verify"):
                compare(source,provenance,p/"out",30,1)

if __name__=="__main__":unittest.main()
