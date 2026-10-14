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
