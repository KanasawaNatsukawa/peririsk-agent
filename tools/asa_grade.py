"""工具 3：调用本地 ASA 规则引擎。"""

from asa_risk import assess_asa


SCHEMA = {
    "type": "function",
    "function": {
        "name": "assess_asa_grade",
        "description": (
            "根据患者情况计算 ASA 麻醉分级，已把收缩压（高血压）纳入判断。"
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
            },
            "required": [
                "age",
                "coronary_heart_disease",
                "diabetes",
                "kidney_failure",
                "unstable",
                "systolic_bp",
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
):
    grade = assess_asa(
        age,
        coronary_heart_disease,
        diabetes,
        kidney_failure,
        unstable,
        systolic_bp,
    )
    return {"ASA分级": grade}
