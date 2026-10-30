"""最终报告程序化校验的回归测试。"""

import unittest

from report_guard import validate_report


VALID_REPORT = """【风险评估】
- 患者收缩压146mmHg，需关注血压管理。（依据：病历工具返回收缩压146mmHg）
- 算法心率85.0次/分，监护仪PLETH_HR 86.2次/分。（依据：心率工具返回算法心率85.0、PLETH_HR 86.2）

【麻醉关注点】
- 术中持续监测血压与心率。（依据：ASA规则引擎判定 II级）

【建议】
- 按ASA II级进行常规术前准备。（依据：ASA规则引擎判定 II级）
"""


class TestReportGuard(unittest.TestCase):
    def test_valid_report_passes(self):
        result = validate_report(VALID_REPORT)
        self.assertTrue(result["通过"])
        self.assertEqual(result["问题"], [])

    def test_forbidden_field_fails(self):
        report = VALID_REPORT.replace(
            "患者收缩压146mmHg",
            "患者为男性，舒张压90mmHg，收缩压146mmHg",
        )
        result = validate_report(report)
        self.assertFalse(result["通过"])
        self.assertTrue(any("禁止字段" in issue for issue in result["问题"]))

    def test_markdown_numbered_sections_pass(self):
        report = VALID_REPORT.replace(
            "【风险评估】",
            "## 一、风险评估",
        ).replace(
            "【麻醉关注点】",
            "## 二、麻醉关注点",
        ).replace(
            "【建议】",
            "## 三、建议",
        )
        result = validate_report(report)
        self.assertTrue(result["通过"], result["问题"])

    def test_bold_numbered_sections_pass(self):
        report = VALID_REPORT.replace(
            "【风险评估】",
            "**一、风险评估**",
        ).replace(
            "【麻醉关注点】",
            "**二、麻醉关注点**",
        ).replace(
            "【建议】",
            "**三、建议**",
        )
        result = validate_report(report)
        self.assertTrue(result["通过"], result["问题"])

    def test_title_alone_does_not_count_as_section(self):
        report = "# 术前风险评估报告\n\n- 没有正文依据。"
        result = validate_report(report)
        self.assertFalse(result["通过"])
        self.assertTrue(any("缺少必需章节" in issue for issue in result["问题"]))

    def test_missing_section_and_evidence_fail(self):
        report = """【风险评估】
- 患者收缩压146mmHg。

【建议】
- 进行常规术前准备。
"""
        result = validate_report(report)
        self.assertFalse(result["通过"])
        self.assertTrue(any("缺少必需章节" in issue for issue in result["问题"]))
        self.assertGreater(result["缺少证据条数"], 0)
