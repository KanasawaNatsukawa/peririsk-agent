"""多病例对齐心率工具的回归测试。"""

import unittest

from patient import PATIENT_WAVEFORMS
from tools import TOOL_FUNCTIONS, TOOLS
from tools import waveform


class TestAlignedWaveform(unittest.TestCase):
    def test_five_distinct_waveforms_are_mapped(self):
        self.assertEqual(len(PATIENT_WAVEFORMS), 5)
        self.assertEqual(len(set(PATIENT_WAVEFORMS.values())), 5)
        for waveform_id in PATIENT_WAVEFORMS.values():
            self.assertTrue(
                (waveform.CASES_DIR / waveform_id / "waveform_60s.csv").exists()
            )

    def test_tool_registry_contains_three_tools(self):
        expected = {
            "get_patient_record",
            "analyze_waveform",
            "assess_asa_grade",
        }
        self.assertEqual(set(TOOL_FUNCTIONS), expected)
        self.assertEqual(
            {tool["function"]["name"] for tool in TOOLS},
            expected,
        )

    def test_each_case_has_expected_sixty_second_result(self):
        expected = {
            "case_001": (87.0, 87.8, 82.6),
            "case_002": (79.0, 80.4, 78.0),
            "case_003": (71.0, 71.4, 70.7),
            "case_004": (85.0, 86.2, 85.5),
            "case_005": (98.0, 101.8, 101.1),
        }
        for waveform_id, (algorithm, pleth_hr, hr) in expected.items():
            with self.subTest(waveform_id=waveform_id):
                result = waveform.analyze_waveform(60, waveform_id=waveform_id)
                self.assertEqual(result["波形ID"], waveform_id)
                self.assertEqual(result["分析时长秒"], 60)
                self.assertEqual(result["算法心率"], algorithm)
                self.assertEqual(result["PLETH_HR"], pleth_hr)
                self.assertEqual(result["HR"], hr)


if __name__ == "__main__":
    unittest.main()
