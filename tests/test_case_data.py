"""病例数据质量和跨窗口心率工具的回归测试。"""

import unittest

from patient import PATIENT_CHEN, PATIENT_ZHAO
from runtime_state import set_patient
from tools.case_data import validate_case_data
from tools.window_stability import compare_hr_windows


class TestCaseData(unittest.TestCase):
    def test_case_data_is_ready_for_current_cases(self):
        for patient in (PATIENT_CHEN, PATIENT_ZHAO):
            with self.subTest(patient=patient["姓名"]):
                set_patient(patient)
                result = validate_case_data(segment_seconds=60)
                self.assertTrue(result["病历字段完整"])
                self.assertTrue(result["是否可以继续分析"])
                self.assertEqual(result["原始数据时长秒"], 120)
                self.assertEqual(result["采样点数"], 30000)
                self.assertEqual(result["波形质量"], "通过")
                self.assertEqual(result["异常采样点"], 0)
                if patient["姓名"] == "陈伟":
                    self.assertEqual(result["选择窗口起始秒"], 45)
                else:
                    self.assertEqual(result["选择窗口起始秒"], 25)

    def test_window_comparison_uses_selected_window(self):
        set_patient(PATIENT_CHEN)
        stable = compare_hr_windows(windows_seconds=[30, 60])
        self.assertEqual(stable["波形ID"], "case_004")
        self.assertEqual(stable["比较窗口秒"], [30, 60])
        self.assertTrue(stable["是否稳定"])

        set_patient(PATIENT_ZHAO)
        unstable = compare_hr_windows(windows_seconds=[30, 60])
        self.assertEqual(unstable["波形ID"], "case_005")
        self.assertEqual(unstable["比较窗口起始秒"], 25)
        self.assertTrue(unstable["是否稳定"])
        self.assertLessEqual(unstable["最大心率差"], 3)
