# ============================================================
# PeriRisk Demo · 第 3 步：按规则把患者信息变成风险等级（ASA 分级）
# 目的：学会"规则判断"——这是 Agent 里评分逻辑的原型。
# 用法：python asa_risk.py
# ============================================================

# ---- 1) 写一个"判断函数"：输入患者情况，输出 ASA 等级 ----
# 规则是演示用的简化版：真实评估由医生结合检查结果综合判断

# 等级数字 → 统一文案；内部先用数字定级，方便"取较高级别"的比较
GRADE_TEXT = {
    1: "I 级（健康）",
    2: "II 级（轻度系统性疾病）",
    3: "III 级（重度系统性疾病，活动受限）",
    4: "IV 级（重度疾病，随时威胁生命）",
    5: "V 级（濒死，不手术无法存活）",
}


def assess_asa(age, has_heart_disease, has_diabetes, has_kidney_failure, unstable,
               systolic_bp=None):
    """按简化规则算 ASA 分级。

    systolic_bp：收缩压（mmHg），不传（None）表示不考虑血压，
    这样旧调用方一行不改也能继续运行。
    血压只负责"抬高级别"：先按原规则定一个基础级别，再算血压给出的地板级别，
    两者取高——高血压不会让一个原本 IV/V 级的患者被降级。
    """
    # ---- 基础规则（原有逻辑，一字未动，只是改用数字表示）----
    if unstable:                      # 病情不稳定 → 高危
        level = 5 if age >= 80 else 4
    elif has_kidney_failure and has_heart_disease:   # 两种重病叠加
        level = 4
    elif has_heart_disease or has_diabetes:          # 有其中一种慢性病
        level = 3
    elif age >= 65:                  # 高龄但健康
        level = 2
    else:
        level = 1

    # ---- 血压地板：未控制的高血压本身构成系统性疾病 ----
    # 演示阈值（参考高血压分级做了简化）：
    #   ≥180 mmHg        → 至少 III 级（重度升高，围术期风险显著）
    #   140~179 mmHg     → 至少 II 级（轻中度升高）
    #   <140 或未提供    → 不抬高
    bp_floor = 0
    if systolic_bp is not None:
        if systolic_bp >= 180:
            bp_floor = 3
        elif systolic_bp >= 140:
            bp_floor = 2

    return GRADE_TEXT[max(level, bp_floor)]


# ---- 2) 演示代码：直接运行本文件时才执行（python asa_risk.py 可看到效果）----
# 包在 __main__ 保护里：被别的模块 import 时不会执行，避免打印干扰主流程
if __name__ == "__main__":
    # 模拟一个患者（字典 = 一张"患者档案卡"）
    patient = {
        "姓名": "张三",
        "年龄": 68,
        "冠心病": True,       # 有冠心病史
        "糖尿病": False,
        "肾功能不全": False,
        "病情不稳定": False,
        "收缩压": 158,        # 偏高，但冠心病已把级别定到 III，血压不再改变结果
    }
    grade = assess_asa(
        patient["年龄"],
        patient["冠心病"],
        patient["糖尿病"],
        patient["肾功能不全"],
        patient["病情不稳定"],
        patient["收缩压"],
    )
    print(f"患者 {patient['姓名']}（{patient['年龄']} 岁）→ ASA {grade}")
