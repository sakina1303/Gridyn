"""A JSON protocol preserves paired truth, failures and equivalent metrics."""

import tempfile
import unittest
from pathlib import Path

from energy_lab.experiments.runner import load_spec, run_experiment


class ExperimentRunnerTests(unittest.TestCase):
    def test_rerun_reproduces_truth_and_outcomes(self):
        spec = load_spec(Path("configs/experiments/paired_missingness.json"))
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = run_experiment(spec, Path(first_dir))[0]
            second = run_experiment(spec, Path(second_dir))[0]
            self.assertEqual(first["run_id"], second["run_id"])
            self.assertEqual(first["truth_sha256"], second["truth_sha256"])
            self.assertEqual(first["results"], second["results"])
            self.assertTrue((Path(first_dir) / first["run_id"] / "truth.json").exists())
            self.assertTrue((Path(first_dir) / first["run_id"] / "observed-paired-missingness-demo-gap-7.json").exists())
            self.assertEqual([item["status"] for item in first["results"]],
                             ["delivered", "abstained", "abstained"])


if __name__ == "__main__":
    unittest.main()
