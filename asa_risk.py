# ============================================================
# PeriRisk Demo · 第 3 步：按规则把患者信息变成风险等级（ASA 分级）
# 目的：学会"规则判断"——这是 Agent 里评分逻辑的原型。
# 用法：python asa_risk.py
# ============================================================

# ---- 1) 写一个"判断函数"：输入患者情况，输出 ASA 等级 ----
# 规则是演示用的简化版：真实评估由医生结合检查结果综合判断
def assess_asa(age, has_heart_disease, has_diabetes, has_kidney_failure, unstable):
    if unstable:                      # 病情不稳定 → 高危
        return "V 级（濒死，不手术无法存活）" if age >= 80 else "IV 级（重度疾病，随时威胁生命）"
    if has_kidney_failure and has_heart_disease:   # 两种重病叠加
        return "IV 级（重度疾病，随时威胁生命）"
    if has_heart_disease or has_diabetes:          # 有其中一种慢性病
        return "III 级（重度系统性疾病，活动受限）"
    if age >= 65:                     # 高龄但健康
        return "II 级（轻度系统性疾病）"
    return "I 级（健康）"


# ---- 2) 模拟一个患者（字典 = 一张"患者档案卡"）----
patient = {
    "姓名": "张三",
    "年龄": 68,
    "冠心病": True,       # 有冠心病史
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": False,
}

# ---- 3) 调用函数，把结果打印出来 ----
grade = assess_asa(
    patient["年龄"],
    patient["冠心病"],
    patient["糖尿病"],
    patient["肾功能不全"],
    patient["病情不稳定"],
)
print(f"患者 {patient['姓名']}（{patient['年龄']} 岁）→ ASA {grade}")
