"""多病例对齐心率工具的回归测试。"""

import unittest

from patient import PATIENT_WAVEFORMS
from tools import TOOL_FUNCTIONS, TOOLS
from tools import waveform


class TestAlignedWaveform(unittest.TestCase):
    def test_twenty_distinct_waveforms_are_mapped(self):
        self.assertEqual(len(PATIENT_WAVEFORMS), 20)
        self.assertEqual(len(set(PATIENT_WAVEFORMS.values())), 20)
        for waveform_id in PATIENT_WAVEFORMS.values():
            self.assertTrue(
                (waveform.CASES_DIR / waveform_id / "waveform_120s.csv").exists()
            )
            pleth, _ = waveform._load_case_data(waveform_id)
            self.assertEqual(len(pleth), 120 * waveform.FS)

    def test_tool_registry_contains_five_tools(self):
        expected = {
            "get_patient_record",
            "validate_case_data",
            "analyze_waveform",
            "compare_hr_windows",
            "assess_asa_grade",
        }
        self.assertEqual(set(TOOL_FUNCTIONS), expected)
        self.assertEqual(
            {tool["function"]["name"] for tool in TOOLS},
            expected,
        )

    def test_each_case_has_expected_sixty_second_result(self):
        expected = {
            "case_001": (5, 87.0, 87.8, 82.7),
            "case_002": (5, 78.0, 78.4, 77.7),
            "case_003": (10, 73.0, 71.7, 71.2),
            "case_004": (45, 86.0, 86.4, 84.2),
            "case_005": (25, 101.0, 100.3, 101.5),
            "case_006": (25, 82.0, 80.8, 80.6),
            "case_008": (20, 54.0, 54.3, 53.8),
            "case_009": (5, 90.0, 89.0, 89.4),
            "case_010": (5, 82.0, 82.4, 81.7),
            "case_011": (35, 84.0, 83.1, 82.8),
            "case_014": (20, 90.0, 86.9, 84.3),
            "case_015": (10, 91.0, 93.5, 92.7),
            "case_016": (0, 60.0, 59.6, 59.1),
            "case_017": (25, 70.0, 70.5, 66.6),
            "case_019": (0, 88.0, 89.4, 89.0),
            "case_020": (45, 95.0, 97.5, 97.5),
            "case_021": (55, 70.0, 65.4, 65.3),
            "case_022": (5, 61.0, 59.1, 58.5),
            "case_023": (5, 75.0, 74.0, 73.6),
            "case_024": (60, 90.0, 90.3, 89.4),
        }
        for waveform_id, (start, algorithm, pleth_hr, hr) in expected.items():
            with self.subTest(waveform_id=waveform_id):
                result = waveform.analyze_waveform(60, waveform_id=waveform_id)
                self.assertEqual(result["波形ID"], waveform_id)
                self.assertEqual(result["原始数据时长秒"], 120)
                self.assertEqual(result["分析窗口起始秒"], start)
                self.assertEqual(result["分析时长秒"], 60)
                self.assertEqual(result["算法心率"], algorithm)
                self.assertEqual(result["PLETH_HR"], pleth_hr)
                self.assertEqual(result["HR"], hr)


if __name__ == "__main__":
    unittest.main()
