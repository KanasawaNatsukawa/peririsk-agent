"""患者花名册与批量评估病例的一致性测试。"""

import unittest

from asa_risk import GRADE_TEXT
from patient import EVALUATION_CASES, PATIENTS, assess_patient


class TestPatientRoster(unittest.TestCase):
    def test_roster_has_twenty_cases(self):
        self.assertEqual(len(PATIENTS), 20)
        self.assertEqual(len(EVALUATION_CASES), 20)

    def test_roster_and_evaluation_use_same_patients_in_order(self):
        roster_names = [patient["姓名"] for patient in PATIENTS.values()]
        evaluation_names = [patient["姓名"] for _, patient in EVALUATION_CASES]
        self.assertEqual(roster_names, evaluation_names)

    def test_expected_asa_grades(self):
        expected = {
            "张三": 3,
            "李四": 1,
            "王秀兰": 2,
            "陈伟": 2,
            "赵芳": 5,
            "郑凯": 3,
            "孙梅": 3,
            "刘强": 3,
            "周敏": 3,
            "吴杰": 1,
            "何丽": 4,
            "马超": 1,
            "高云": 2,
            "林浩": 3,
            "许娟": 3,
            "胡军": 3,
            "唐雅": 1,
            "宋磊": 4,
            "罗萍": 2,
            "曹宁": 3,
        }
        for name, level in expected.items():
            patient = next(p for p in PATIENTS.values() if p["姓名"] == name)
            self.assertEqual(assess_patient(patient), GRADE_TEXT[level])


if __name__ == "__main__":
    unittest.main()
