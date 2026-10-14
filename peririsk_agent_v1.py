# ============================================================
# PeriRisk Demo · 第 4 步：PeriRisk Agent v1 —— 让 DeepSeek 写风险评估报告
# 用法：python peririsk_agent_v1.py
# ============================================================

from openai import OpenAI
from asa_risk import assess_asa   # 复用第 3 步写好的评分函数

# ---- 0) 连接 DeepSeek（和 test_deepseek.py 一样）----
API_KEY = "sk-在这里粘贴你的key"   # ← 再粘贴一次你的 key
client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

# ---- 1) 患者信息（病历摘要）----
patient = {
    "姓名": "张三",
    "年龄": 68,
    "冠心病": True,        # 有冠心病史
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": False,
    "心率": 92,            # ← 正式 Demo 里，这个数来自第 2 步的波形计算
    "收缩压": 158,         # 血压偏高
}

# ---- 2) 程序算出"硬指标"：ASA 等级 + 整理成一段摘要 ----
grade = assess_asa(
    patient["年龄"],
    patient["冠心病"],
    patient["糖尿病"],
    patient["肾功能不全"],
    patient["病情不稳定"],
)
summary = (
    f"患者{patient['姓名']}，{patient['年龄']}岁，"
    f"ASA分级（程序计算）：{grade}，"
    f"心率 {patient['心率']} 次/分钟，收缩压 {patient['收缩压']} mmHg，"
    f"既往史：冠心病{'是' if patient['冠心病'] else '否'}、"
    f"糖尿病{'是' if patient['糖尿病'] else '否'}。"
)

# ---- 3) 把摘要发给 DeepSeek，请它写报告 ----
reply = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {
            "role": "system",
            "content": (
                "你是一名资深麻醉科医生。请根据患者信息输出一份术前风险评估报告，"
                "格式必须包含三部分：【风险评估】【麻醉关注点】【建议】。"
                "必须引用给出的数值，不要编造患者没有的病史。"
            ),
        },
        {"role": "user", "content": f"患者信息如下，请出报告：{summary}"},
    ],
)

# ---- 4) 打印报告 ----
print(reply.choices[0].message.content)
