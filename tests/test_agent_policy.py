"""Agent 对完整报告和限定任务的路径判断测试。"""

import unittest

from peririsk_agent import MAX_ROUNDS, _needs_report_guard


class TestAgentPolicy(unittest.TestCase):
    def test_agent_round_limit_is_ten(self):
        self.assertEqual(MAX_ROUNDS, 10)

    def test_heart_rate_only_task_skips_full_report_guard(self):
        task = "只计算当前患者的心率，不评估ASA，也不要生成完整术前风险评估报告。"
        report = "当前患者算法心率为85.0次/分。"
        self.assertFalse(_needs_report_guard(task, report))

    def test_complete_assessment_requires_report_guard(self):
        task = "请为当前患者完成完整术前风险评估并输出报告。"
        report = "# 报告\n\n当前内容尚未完成。"
        self.assertTrue(_needs_report_guard(task, report))

    def test_report_sections_trigger_guard_even_with_short_task(self):
        task = "请处理当前数据。"
        report = "【风险评估】\n- 示例结论。"
        self.assertTrue(_needs_report_guard(task, report))


if __name__ == "__main__":
    unittest.main()
