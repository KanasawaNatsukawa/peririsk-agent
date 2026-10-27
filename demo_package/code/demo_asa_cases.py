"""现场演示：四个 ASA 输入，直接展示规则引擎的确定性输出。

不依赖第三方库，不调用 API，只需要 Python。
"""

from asa_risk import assess_asa


CASES = [
    {
        "label": "50岁，无基础病，血压146",
        "args": (50, False, False, False, False, 146),
    },
    {
        "label": "55岁，有糖尿病，血压185",
        "args": (55, False, True, False, False, 185),
    },
    {
        "label": "82岁，病情不稳定，血压92",
        "args": (82, False, False, False, True, 92),
    },
    {
        "label": "60岁，冠心病+肾功能不全，血压130",
        "args": (60, True, False, True, False, 130),
    },
]


if __name__ == "__main__":
    print("PeriRisk ASA 规则演示（本地计算，不调用大模型）")
    print("=" * 58)
    for case in CASES:
        grade = assess_asa(*case["args"])
        print(f"{case['label']} -> {grade}")
