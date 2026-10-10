"""Research documentation automation contract tests; no external data."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "research_archive.py"
spec = importlib.util.spec_from_file_location("research_archive", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ResearchArchiveTests(unittest.TestCase):
    def test_archive_and_verify_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            repo = root / "repo"
            repo.mkdir()
            run = root / "run"
            run.mkdir()
            (run / "frames.csv").write_text("frame,error\n1,0.4\n")
            dest = root / "fingerprint"
            result = module.archive(repo, run, dest, "synthetic functional test")
            self.assertEqual(result["evidence_count"], 1)
            self.assertFalse(result["qualification"]["hardware_vrs_speedup_confirmed"])
            self.assertTrue(module.verify(dest / "evidence_manifest.json")["ok"])
            (run / "frames.csv").write_text("frame,error\n1,0.5\n")
            observed = module.verify(dest / "evidence_manifest.json")
            self.assertFalse(observed["ok"])
            self.assertEqual(observed["changed"], 1)
            with self.assertRaises(FileExistsError):
                module.archive(repo, run, dest, "overwrite attempt")

    def test_inventory_collects_actual_python_functions(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "foveabench").mkdir()
            (root / "tests").mkdir()
            (root / "foveabench" / "sample.py").write_text("class A:\n    def foo(self):\n        return 1\n")
            (root / "tests" / "test_sample.py").write_text("def test_x():\n    assert True\n")
            result = module.inventory(root, root / "inventory")
            self.assertEqual(result["tracked_files_indexed"], 2)
            self.assertEqual(result["declared_python_test_methods"], 1)
            self.assertIn("A.foo", [x["symbol"] for x in result["files"][0]["declarations"]])

    def test_refuses_recursive_archive_and_empty_runs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a").mkdir()
            with self.assertRaises(ValueError):
                module.archive(root, root / "a", root / "a" / "archive", "bad")
            with self.assertRaises(ValueError):
                module.archive(root, root / "a", root / "output", "empty")


if __name__ == "__main__":
    unittest.main()
