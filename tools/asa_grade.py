"""工具 3：调用本地 ASA 规则引擎。"""

from asa_risk import assess_asa


SCHEMA = {
    "type": "function",
    "function": {
        "name": "assess_asa_grade",
        "description": (
            "根据患者情况计算 ASA 麻醉分级，已纳入收缩压、BMI 和活动性"
            "恶性肿瘤；急诊手术返回 E 标识，困难气道返回围术期关注提示。"
            "调用前需要先查病历拿到各项信息。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "description": "年龄（岁）"},
                "coronary_heart_disease": {
                    "type": "boolean",
                    "description": "是否有冠心病",
                },
                "diabetes": {
                    "type": "boolean",
                    "description": "是否有糖尿病",
                },
                "kidney_failure": {
                    "type": "boolean",
                    "description": "是否有肾功能不全",
                },
                "unstable": {
                    "type": "boolean",
                    "description": "病情是否不稳定",
                },
                "systolic_bp": {
                    "type": "integer",
                    "description": "收缩压（mmHg），来自病历",
                },
                "bmi": {
                    "type": "number",
                    "description": "体重指数 BMI（kg/m²），来自病历",
                },
                "active_malignancy": {
                    "type": "boolean",
                    "description": "是否有活动性恶性肿瘤",
                },
                "emergency_surgery": {
                    "type": "boolean",
                    "description": "是否为急诊手术；只追加 ASA 的 E 标识",
                },
                "difficult_airway": {
                    "type": "boolean",
                    "description": "是否存在困难气道；不改变 ASA 数字等级",
                },
            },
            "required": [
                "age",
                "coronary_heart_disease",
                "diabetes",
                "kidney_failure",
                "unstable",
                "systolic_bp",
                "bmi",
                "active_malignancy",
                "emergency_surgery",
                "difficult_airway",
            ],
        },
    },
}


def assess_asa_grade(
    age,
    coronary_heart_disease,
    diabetes,
    kidney_failure,
    unstable,
    systolic_bp=None,
    bmi=None,
    active_malignancy=False,
    emergency_surgery=False,
    difficult_airway=False,
):
    grade = assess_asa(
        age,
        coronary_heart_disease,
        diabetes,
        kidney_failure,
        unstable,
        systolic_bp,
        bmi,
        active_malignancy,
    )
    return {
        "ASA分级": grade,
        "急诊标识": "E" if emergency_surgery else "无",
        "困难气道关注": "需要困难气道预案" if difficult_airway else "无",
    }
