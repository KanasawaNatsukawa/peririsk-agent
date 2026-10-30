"""数字孪生推演舱纯逻辑测试。"""

import unittest

from patient import PATIENT_CHEN
from tools.waveform import (
    _display_invalid_sample_mask,
    _load_case_data,
)
from twin_lab import (
    asa_breakdown,
    candidate_quality_view,
    scenario_path,
    waveform_view,
)


class TestTwinLab(unittest.TestCase):
    def test_blood_pressure_slider_changes_asa(self):
        normal = asa_breakdown(PATIENT_CHEN, 146)
        elevated = asa_breakdown(PATIENT_CHEN, 185)
        self.assertEqual(normal["最终级别"], 2)
        self.assertEqual(elevated["最终级别"], 3)

    def test_missing_blood_pressure_blocks_grading(self):
        result = asa_breakdown(PATIENT_CHEN, None)
        self.assertIsNone(result["最终级别"])
        self.assertIn("无法可靠分级", result["最终分级"])

    def test_extended_asa_inputs_change_level_and_modifiers(self):
        elevated = asa_breakdown(
            PATIENT_CHEN,
            146,
            bmi=41,
            active_malignancy=True,
            emergency_surgery=True,
            difficult_airway=True,
        )
        self.assertEqual(elevated["最终级别"], 3)
        self.assertEqual(elevated["急诊标识"], "E")
        self.assertTrue(elevated["困难气道"])

    def test_waveform_view_and_flatline(self):
        normal = waveform_view("case_004", display_seconds=10)
        self.assertGreater(normal["显示窗口峰数"], 0)
        self.assertGreater(len(normal["waveform"]), 0)
        self.assertEqual(normal["工具选择起始秒"], 45)
        self.assertEqual(normal["波形质量"], "通过")
        self.assertEqual(normal["异常采样点"], 0)

        flat = waveform_view("case_004", display_seconds=10, flatline=True)
        self.assertEqual(flat["显示窗口峰数"], 0)
        self.assertEqual(flat["波形质量"], "不足")

    def test_tool_selection_avoids_raw_artifact_windows(self):
        expected = {
            "case_002": (5, 850),
            "case_003": (10, 350),
            "case_004": (45, 6),
        }
        for waveform_id, (selected_start, raw_anomalies) in expected.items():
            with self.subTest(waveform_id=waveform_id):
                raw, _ = _load_case_data(waveform_id)
                selected = waveform_view(waveform_id, display_seconds=20)
                self.assertEqual(selected["工具选择起始秒"], selected_start)
                self.assertEqual(selected["异常采样点"], 0)
                self.assertEqual(int(_display_invalid_sample_mask(raw).sum()), raw_anomalies)

    def test_sixty_second_window_is_available(self):
        result = waveform_view("case_004", display_seconds=60)
        self.assertEqual(result["显示窗口秒"], 60)
        self.assertEqual(result["工具选择起始秒"], 45)
        self.assertEqual(result["显示窗口峰数"], 86)
        self.assertEqual(result["60秒峰数"], 86)
        self.assertAlmostEqual(
            float(result["waveform"]["time"].max()),
            59.99,
            places=2,
        )

    def test_candidate_quality_view_contains_all_windows(self):
        quality = candidate_quality_view("case_004")
        candidates = quality["候选窗口"]
        self.assertEqual(quality["原始数据时长秒"], 120)
        self.assertEqual(quality["候选窗口数"], 13)
        self.assertEqual(len(candidates), 13)
        self.assertEqual(sum(item["是否选中"] for item in candidates), 1)
        self.assertEqual(candidates[0]["质量排名"], 1)
        self.assertEqual(candidates[0]["起始秒"], 45)
        self.assertEqual(candidates[0]["结束秒"], 105)
        self.assertIn("同源差", candidates[0])
        self.assertIn("综合HR差", candidates[0])
        policies = {
            item["策略"]: item
            for item in quality["策略对比"]
        }
        self.assertEqual(len(policies), 4)
        self.assertEqual(policies["固定首窗"]["窗口起始秒"], 0)
        self.assertEqual(policies["质量+稳定性"]["窗口起始秒"], 45)
        self.assertTrue(policies["参考最优"]["使用参考心率选窗"])
        self.assertFalse(policies["质量+稳定性"]["使用参考心率选窗"])

    def test_conflict_scenario_uses_stability_tool(self):
        path = scenario_path("心率冲突", conflict=True)
        self.assertIn("compare_hr_windows", path)


if __name__ == "__main__":
    unittest.main()
