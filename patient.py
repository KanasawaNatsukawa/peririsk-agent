# ============================================================
# PeriRisk Demo · 公共模块：患者档案 + 摘要拼接
# 全项目共用这一张"病历卡"——以后换患者、改摘要写法，只改这一个文件。
# ============================================================

from asa_risk import assess_asa   # 复用第 3 步的规则引擎（纯逻辑，不调 AI）

# ---- 患者档案（演示用假设数据；真实场景来自医院 HIS 系统）----
PATIENT = {
    "姓名": "张三",
    "年龄": 68,
    "冠心病": True,
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": False,
    "收缩压": 158,   # 来自病历（监护仪血压通道存在校准偏置，此处用病历值）
}

# ---- 对比患者：低风险（字段与 PATIENT 完全一致，演示同一套 Agent 对不同患者的差异）----
PATIENT_LOW_RISK = {
    "姓名": "李四",
    "年龄": 45,
    "冠心病": False,
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": False,
    "收缩压": 120,   # 正常血压
}

# ---- 边界与危重病例：与网页、批量评估共用同一批档案卡 ----
PATIENT_WANG = {
    "姓名": "王秀兰",
    "年龄": 72,
    "冠心病": False,
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": False,
    "收缩压": 126,
}

PATIENT_CHEN = {
    "姓名": "陈伟",
    "年龄": 50,
    "冠心病": False,
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": False,
    "收缩压": 146,
}

PATIENT_ZHAO = {
    "姓名": "赵芳",
    "年龄": 82,
    "冠心病": False,
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": True,
    "收缩压": 92,
}

# ---- 患者花名册：界面下拉框按"标签 → 档案卡"切换 ----
# 第一项是默认的高风险患者，保证不选时行为和以前完全一样
PATIENTS = {
    "高风险患者 · 张三（68岁，冠心病）": PATIENT,
    "低风险患者 · 李四（45岁，既往健康）": PATIENT_LOW_RISK,
    "边界患者 · 王秀兰（72岁，无基础病）": PATIENT_WANG,
    "边界患者 · 陈伟（50岁，轻度高血压）": PATIENT_CHEN,
    "危重患者 · 赵芳（82岁，病情不稳定）": PATIENT_ZHAO,
}

# ---- 批量评估的短标签：只复用上面的档案卡，不再复制患者数据 ----
EVALUATION_CASES = [
    ("高风险·冠心病老人", PATIENT),
    ("低风险·健康中年", PATIENT_LOW_RISK),
    ("边界·老年无基础病", PATIENT_WANG),
    ("边界·中年轻度高血压", PATIENT_CHEN),
    ("危重·病情不稳定", PATIENT_ZHAO),
]

# ---- 患者与 VitalDB 波形的一一绑定：网页选患者时自动切换对应病例 ----
PATIENT_WAVEFORMS = {
    "张三": "case_001",
    "李四": "case_002",
    "王秀兰": "case_003",
    "陈伟": "case_004",
    "赵芳": "case_005",
}
DEFAULT_WAVEFORM_ID = "case_001"


def assess_patient(patient):
    """直接吃一张患者档案卡（dict），内部转调规则引擎 assess_asa。

    好处：主脚本不用每次手写 5 个参数，字典加字段也不影响调用方。
    """
    return assess_asa(
        patient["年龄"],
        patient["冠心病"],
        patient["糖尿病"],
        patient["肾功能不全"],
        patient["病情不稳定"],
        patient["收缩压"],
    )


def build_summary(patient, grade, hr, hr_note="", sbp_note=""):
    """把病历 + 程序算出的硬指标（分级、心率）拼成一段话。

    hr_note / sbp_note 是给数值补的"来源小尾巴"，
    比如"（由监护波形自动计算）"，演示时观众能看懂数据从哪来。
    不传就保持和第 4 步初版完全一样的摘要。
    """
    return (
        f"患者{patient['姓名']}，{patient['年龄']}岁，"
        f"ASA分级（程序计算）：{grade}，"
        f"心率 {hr:.0f} 次/分钟{hr_note}，"
        f"收缩压 {patient['收缩压']} mmHg{sbp_note}，"
        f"既往史：冠心病{'是' if patient['冠心病'] else '否'}、"
        f"糖尿病{'是' if patient['糖尿病'] else '否'}。"
    )
