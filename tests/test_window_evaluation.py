"""全候选窗口评估输出的回归测试。"""

import csv
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from evaluate import evaluate_all_windows, search_heart_rate_parameters


class TestWindowEvaluation(unittest.TestCase):
    def test_all_candidate_windows_are_exported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with redirect_stdout(io.StringIO()):
                results, summaries, policies, policy_summary = (
                    evaluate_all_windows(temp_dir)
                )

            self.assertEqual(len(results), 260)
            self.assertEqual(len(summaries), 21)
            self.assertEqual(len(policies), 80)
            self.assertEqual(len(policy_summary), 4)
            self.assertEqual(
                sum(row["是否选中"] == "是" for row in results),
                20,
            )

            results_path = Path(temp_dir) / "window_evaluation_results.csv"
            summary_path = Path(temp_dir) / "window_evaluation_summary.csv"
            policy_path = Path(temp_dir) / "window_policy_comparison.csv"
            with open(results_path, encoding="utf-8-sig") as f:
                self.assertEqual(len(list(csv.DictReader(f))), 260)
            with open(summary_path, encoding="utf-8-sig") as f:
                self.assertEqual(len(list(csv.DictReader(f))), 21)
            with open(policy_path, encoding="utf-8-sig") as f:
                self.assertEqual(len(list(csv.DictReader(f))), 80)

    def test_parameter_search_exports_ranked_grid(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with redirect_stdout(io.StringIO()):
                rows = search_heart_rate_parameters(
                    prominences=[0.4, 0.5],
                    min_distances=[0.4],
                    output_dir=temp_dir,
                )

            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["综合排名"], 1)
            self.assertEqual(rows[1]["综合排名"], 2)
            self.assertLessEqual(
                rows[0]["稳健评分"],
                rows[1]["稳健评分"],
            )
            search_path = Path(temp_dir) / "heart_rate_parameter_search.csv"
            with open(search_path, encoding="utf-8-sig") as f:
                self.assertEqual(len(list(csv.DictReader(f))), 2)


if __name__ == "__main__":
    unittest.main()
