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
    "BMI": 26.8,
    "活动性恶性肿瘤": False,
    "急诊手术": False,
    "困难气道": False,
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
    "BMI": 23.1,
    "活动性恶性肿瘤": False,
    "急诊手术": False,
    "困难气道": False,
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
    "BMI": 31.5,
    "活动性恶性肿瘤": False,
    "急诊手术": False,
    "困难气道": False,
}

PATIENT_CHEN = {
    "姓名": "陈伟",
    "年龄": 50,
    "冠心病": False,
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": False,
    "收缩压": 146,
    "BMI": 34.2,
    "活动性恶性肿瘤": False,
    "急诊手术": False,
    "困难气道": True,
}

PATIENT_ZHAO = {
    "姓名": "赵芳",
    "年龄": 82,
    "冠心病": False,
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": True,
    "收缩压": 92,
    "BMI": 24.7,
    "活动性恶性肿瘤": False,
    "急诊手术": True,
    "困难气道": False,
}

# ---- 扩展演示病例：人物信息均为合成，波形来自公开 VitalDB 病例 ----
PATIENT_ZHENG = {
    "姓名": "郑凯",
    "年龄": 56,
    "冠心病": False,
    "糖尿病": True,
    "肾功能不全": False,
    "病情不稳定": False,
    "收缩压": 152,
    "BMI": 36.4,
    "活动性恶性肿瘤": False,
    "急诊手术": False,
    "困难气道": False,
}

PATIENT_SUN = {
    "姓名": "孙梅",
    "年龄": 61,
    "冠心病": False,
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": False,
    "收缩压": 132,
    "BMI": 28.6,
    "活动性恶性肿瘤": True,
    "急诊手术": False,
    "困难气道": False,
}

PATIENT_LIU = {
    "姓名": "刘强",
    "年龄": 47,
    "冠心病": False,
    "糖尿病": True,
    "肾功能不全": False,
    "病情不稳定": False,
    "收缩压": 126,
    "BMI": 29.3,
    "活动性恶性肿瘤": False,
    "急诊手术": False,
    "困难气道": False,
}

PATIENT_ZHOU = {
    "姓名": "周敏",
    "年龄": 70,
    "冠心病": False,
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": False,
    "收缩压": 138,
    "BMI": 41.2,
    "活动性恶性肿瘤": False,
    "急诊手术": False,
    "困难气道": False,
}

PATIENT_WU = {
    "姓名": "吴杰",
    "年龄": 39,
    "冠心病": False,
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": False,
    "收缩压": 118,
    "BMI": 24.0,
    "活动性恶性肿瘤": False,
    "急诊手术": True,
    "困难气道": False,
}

PATIENT_HE = {
    "姓名": "何丽",
    "年龄": 66,
    "冠心病": True,
    "糖尿病": False,
    "肾功能不全": True,
    "病情不稳定": False,
    "收缩压": 134,
    "BMI": 25.5,
    "活动性恶性肿瘤": False,
    "急诊手术": False,
    "困难气道": False,
}

PATIENT_MA = {
    "姓名": "马超",
    "年龄": 58,
    "冠心病": False,
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": False,
    "收缩压": 124,
    "BMI": 27.4,
    "活动性恶性肿瘤": False,
    "急诊手术": False,
    "困难气道": True,
}

PATIENT_GAO = {
    "姓名": "高云",
    "年龄": 75,
    "冠心病": False,
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": False,
    "收缩压": 130,
    "BMI": 22.5,
    "活动性恶性肿瘤": False,
    "急诊手术": False,
    "困难气道": False,
}

PATIENT_LIN = {
    "姓名": "林浩",
    "年龄": 53,
    "冠心病": False,
    "糖尿病": True,
    "肾功能不全": False,
    "病情不稳定": False,
    "收缩压": 144,
    "BMI": 32.1,
    "活动性恶性肿瘤": False,
    "急诊手术": False,
    "困难气道": False,
}

PATIENT_XU = {
    "姓名": "许娟",
    "年龄": 44,
    "冠心病": False,
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": False,
    "收缩压": 116,
    "BMI": 23.6,
    "活动性恶性肿瘤": True,
    "急诊手术": False,
    "困难气道": False,
}

PATIENT_HU = {
    "姓名": "胡军",
    "年龄": 63,
    "冠心病": True,
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": False,
    "收缩压": 150,
    "BMI": 29.8,
    "活动性恶性肿瘤": False,
    "急诊手术": True,
    "困难气道": False,
}

PATIENT_TANG = {
    "姓名": "唐雅",
    "年龄": 29,
    "冠心病": False,
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": False,
    "收缩压": 110,
    "BMI": 21.2,
    "活动性恶性肿瘤": False,
    "急诊手术": False,
    "困难气道": False,
}

PATIENT_SONG = {
    "姓名": "宋磊",
    "年龄": 59,
    "冠心病": True,
    "糖尿病": False,
    "肾功能不全": True,
    "病情不稳定": False,
    "收缩压": 128,
    "BMI": 28.0,
    "活动性恶性肿瘤": False,
    "急诊手术": False,
    "困难气道": False,
}

PATIENT_LUO = {
    "姓名": "罗萍",
    "年龄": 81,
    "冠心病": False,
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": False,
    "收缩压": 136,
    "BMI": 24.1,
    "活动性恶性肿瘤": False,
    "急诊手术": False,
    "困难气道": False,
}

PATIENT_CAO = {
    "姓名": "曹宁",
    "年龄": 67,
    "冠心病": False,
    "糖尿病": True,
    "肾功能不全": False,
    "病情不稳定": False,
    "收缩压": 142,
    "BMI": 33.0,
    "活动性恶性肿瘤": False,
    "急诊手术": False,
    "困难气道": True,
}

# ---- 患者花名册：界面下拉框按"标签 → 档案卡"切换 ----
# 第一项是默认的高风险患者，保证不选时行为和以前完全一样
PATIENTS = {
    "高风险患者 · 张三（68岁，冠心病）": PATIENT,
    "低风险患者 · 李四（45岁，既往健康）": PATIENT_LOW_RISK,
    "边界患者 · 王秀兰（72岁，无基础病）": PATIENT_WANG,
    "边界患者 · 陈伟（50岁，轻度高血压）": PATIENT_CHEN,
    "危重患者 · 赵芳（82岁，病情不稳定）": PATIENT_ZHAO,
    "糖尿病患者 · 郑凯（56岁，肥胖）": PATIENT_ZHENG,
    "肿瘤患者 · 孙梅（61岁，活动性肿瘤）": PATIENT_SUN,
    "糖尿病患者 · 刘强（47岁）": PATIENT_LIU,
    "重度肥胖 · 周敏（70岁）": PATIENT_ZHOU,
    "急诊患者 · 吴杰（39岁）": PATIENT_WU,
    "心肺肾患者 · 何丽（66岁）": PATIENT_HE,
    "气道风险 · 马超（58岁）": PATIENT_MA,
    "高龄患者 · 高云（75岁）": PATIENT_GAO,
    "糖尿病患者 · 林浩（53岁）": PATIENT_LIN,
    "肿瘤患者 · 许娟（44岁）": PATIENT_XU,
    "冠心病急诊 · 胡军（63岁）": PATIENT_HU,
    "低风险患者 · 唐雅（29岁）": PATIENT_TANG,
    "心肺患者 · 宋磊（59岁）": PATIENT_SONG,
    "高龄患者 · 罗萍（81岁）": PATIENT_LUO,
    "气道风险 · 曹宁（67岁）": PATIENT_CAO,
}

# ---- 批量评估的短标签：只复用上面的档案卡，不再复制患者数据 ----
EVALUATION_CASES = [
    ("高风险·冠心病老人", PATIENT),
    ("低风险·健康中年", PATIENT_LOW_RISK),
    ("边界·老年无基础病", PATIENT_WANG),
    ("边界·中年轻度高血压", PATIENT_CHEN),
    ("危重·病情不稳定", PATIENT_ZHAO),
    ("糖尿病·肥胖", PATIENT_ZHENG),
    ("肿瘤·活动性", PATIENT_SUN),
    ("糖尿病·中年", PATIENT_LIU),
    ("重度肥胖·老年", PATIENT_ZHOU),
    ("急诊·年轻", PATIENT_WU),
    ("心肺肾·合并症", PATIENT_HE),
    ("困难气道·中年", PATIENT_MA),
    ("高龄·健康", PATIENT_GAO),
    ("糖尿病·肥胖", PATIENT_LIN),
    ("肿瘤·活动性", PATIENT_XU),
    ("冠心病·急诊", PATIENT_HU),
    ("低风险·年轻", PATIENT_TANG),
    ("心肺·合并症", PATIENT_SONG),
    ("高龄·健康", PATIENT_LUO),
    ("糖尿病·困难气道", PATIENT_CAO),
]

# ---- 患者与 VitalDB 波形的一一绑定：网页选患者时自动切换对应病例 ----
PATIENT_WAVEFORMS = {
    "张三": "case_001",
    "李四": "case_002",
    "王秀兰": "case_003",
    "陈伟": "case_004",
    "赵芳": "case_005",
    "郑凯": "case_006",
    "孙梅": "case_008",
    "刘强": "case_009",
    "周敏": "case_010",
    "吴杰": "case_011",
    "何丽": "case_014",
    "马超": "case_015",
    "高云": "case_016",
    "林浩": "case_017",
    "许娟": "case_019",
    "胡军": "case_020",
    "唐雅": "case_021",
    "宋磊": "case_022",
    "罗萍": "case_023",
    "曹宁": "case_024",
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
        patient["BMI"],
        patient["活动性恶性肿瘤"],
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
        f"BMI {patient['BMI']}，"
        f"既往史：冠心病{'是' if patient['冠心病'] else '否'}、"
        f"糖尿病{'是' if patient['糖尿病'] else '否'}、"
        f"活动性恶性肿瘤{'是' if patient['活动性恶性肿瘤'] else '否'}；"
        f"急诊手术{'是' if patient['急诊手术'] else '否'}；"
        f"困难气道{'是' if patient['困难气道'] else '否'}。"
    )
