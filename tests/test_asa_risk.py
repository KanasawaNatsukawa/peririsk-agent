"""ASA 规则引擎的回归测试。

目的：把“血压只升不降”和规则优先级固定下来。
以后 AI 再改 asa_risk.py，先跑这组测试，出错就知道改坏了什么。
"""

import unittest

from asa_risk import GRADE_TEXT, assess_asa


class TestAsaRisk(unittest.TestCase):
    def test_bp_140_raises_healthy_to_grade_2(self):
        grade = assess_asa(50, False, False, False, False, 140)
        self.assertEqual(grade, GRADE_TEXT[2])

    def test_bp_139_does_not_raise_healthy(self):
        grade = assess_asa(50, False, False, False, False, 139)
        self.assertEqual(grade, GRADE_TEXT[1])

    def test_bp_180_raises_healthy_to_grade_3(self):
        grade = assess_asa(50, False, False, False, False, 180)
        self.assertEqual(grade, GRADE_TEXT[3])

    def test_coronary_disease_stays_grade_3_with_moderate_bp(self):
        grade = assess_asa(68, True, False, False, False, 158)
        self.assertEqual(grade, GRADE_TEXT[3])

    def test_kidney_and_heart_disease_are_grade_4(self):
        grade = assess_asa(60, True, False, True, False, 130)
        self.assertEqual(grade, GRADE_TEXT[4])

    def test_unstable_age_82_is_grade_5(self):
        grade = assess_asa(82, False, False, False, True, 92)
        self.assertEqual(grade, GRADE_TEXT[5])

    def test_bp_cannot_downgrade_unstable_grade_5(self):
        grade = assess_asa(84, True, False, True, True, 200)
        self.assertEqual(grade, GRADE_TEXT[5])

    def test_healthy_age_72_is_grade_2(self):
        grade = assess_asa(72, False, False, False, False, 126)
        self.assertEqual(grade, GRADE_TEXT[2])

    def test_missing_bp_keeps_legacy_behavior(self):
        grade = assess_asa(68, True, False, False, False, None)
        self.assertEqual(grade, GRADE_TEXT[3])


if __name__ == "__main__":
    unittest.main()
