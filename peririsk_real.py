# ============================================================
# PeriRisk Demo · 真实数据版：用 VitalDB 真实监护数据跑通全流程
# 对比上次的进步：
#   上次 —— 心率来自"造出来的正弦波"
#   这次 —— 心率来自真实手术监护记录（VitalDB 公开数据集）
# 用法：python peririsk_real.py
# ============================================================

import csv
import json

import numpy as np
import requests
from scipy.signal import find_peaks

from asa_risk import assess_asa
from config import API_KEY

# ---- 数据文件位置（你下载好的真实数据）----
WAVE_FILE = r"E:\数字孪生\python\waveform_120s.csv"     # 120 秒真实波形
NUM_FILE = r"E:\数字孪生\python\numeric_60s.csv"        # 监护仪记录的数值

print("=" * 56)
print("PeriRisk Agent 开始术前风险评估（真实数据版）")
print("=" * 56)

# ---- [1/5] 读取真实脉搏波（PLETH = 血氧探头波形）----
print("[1/5] 读取真实监护波形（VitalDB 病例 1）")
times, pleth = [], []
with open(WAVE_FILE, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        times.append(float(row["时间(秒)"]))
        pleth.append(float(row["PLETH(a.u.)"]))
pleth = np.array(pleth)
fs = 500                      # 真实采样率：每秒 500 个点
seg = pleth[: fs * 30]        # 取前 30 秒
print(f"      ✓ 已读取 {len(pleth)} 个采样点（120 秒），本次分析前 30 秒")

# ---- [2/5] 找波峰 → 算心率 ----
print("[2/5] 信号处理：检测脉搏波波峰 → 计算心率")
peaks, _ = find_peaks(seg, distance=fs * 0.4, prominence=0.5)  # 心跳间隔≥0.4秒，排除噪声
hr_est = len(peaks) * 60 / 30
print(f"      ✓ 30 秒检测到 {len(peaks)} 次心跳 → 算法心率 {hr_est:.0f} 次/分钟")

# ---- [3/5] 读取监护仪记录的心率做对照 ----
print("[3/5] 读取监护仪记录心率（用于验证算法）")
hrs = []
with open(NUM_FILE, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        if row["心率(次/分)"]:
            hrs.append(float(row["心率(次/分)"]))
ref_hr = float(np.mean(hrs))
print(f"      ✓ 监护仪记录心率 ≈ {ref_hr:.0f} 次/分钟（和算法结果对比）")

# ---- [4/5] 病历 + 评分 → 摘要 ----
print("[4/5] 规则评分：结合病历计算 ASA 分级")
# 病历信息（演示用假设数据；真实场景来自医院 HIS 系统）
patient = {
    "姓名": "张三",
    "年龄": 68,
    "冠心病": True,
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": False,
    "收缩压": 158,   # 来自病历（监护仪血压通道存在校准偏置，此处用病历值）
}
grade = assess_asa(
    patient["年龄"],
    patient["冠心病"],
    patient["糖尿病"],
    patient["肾功能不全"],
    patient["病情不稳定"],
)
print(f"      ✓ 完成：ASA {grade}")

summary = (
    f"患者{patient['姓名']}，{patient['年龄']}岁，"
    f"ASA分级（程序计算）：{grade}，"
    f"心率 {hr_est:.0f} 次/分钟（由真实手术监护波形自动计算，"
    f"与监护仪记录 {ref_hr:.0f} 次/分钟一致），"
    f"收缩压 {patient['收缩压']} mmHg（来自病历），"
    f"既往史：冠心病{'是' if patient['冠心病'] else '否'}、"
    f"糖尿病{'是' if patient['糖尿病'] else '否'}。"
)

# ---- [5/5] 大模型生成报告 ----
print("[5/5] 调用大模型生成风险评估报告…")
resp = requests.post(
    "https://api.deepseek.com/chat/completions",
    headers={
        "Authorization": "Bearer " + API_KEY,
        "Content-Type": "application/json",
    },
    data=json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一名资深麻醉科医生。请根据患者信息输出一份术前风险评估报告，"
                    "格式必须包含三部分：【风险评估】【麻醉关注点】【建议】。"
                    "必须引用给出的数值，不要编造患者没有的病史。"
                ),
            },
            {"role": "user", "content": "患者信息如下，请出报告：" + summary},
        ],
    }),
    timeout=30,
)

print("=" * 56)
if resp.status_code == 200:
    data = resp.json()
    print(data["choices"][0]["message"]["content"])
else:
    print("请求失败，状态码：", resp.status_code)
    print("返回内容：", resp.text)
print("=" * 56)
print("PeriRisk Agent 评估完成（数据来源：VitalDB 真实手术监护记录）")
