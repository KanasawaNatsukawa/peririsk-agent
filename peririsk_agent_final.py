# ============================================================
# PeriRisk Demo · 第 5 步：PeriRisk Agent 完整版（最终整合）
# 一个脚本走完 Agent 全流程：读波形 → 算心率 → 算分级 → 生成报告
# 用法：
#   1) 记事本打开 config.py，填好 key（只填一次），保存
#   2) 运行  python peririsk_agent_final.py
# ============================================================

import json

import numpy as np
import requests
from scipy.signal import find_peaks

from asa_risk import assess_asa   # 第 3 步的评分函数
from config import API_KEY        # 统一读取你的 key

# ---- 工具 1：从波形算心率（第 2 步的能力，封装成函数）----
def compute_hr_from_wave():
    fs = 100                       # 采样率：每秒 100 个点
    duration = 10                  # 取 10 秒波形
    t = np.arange(0, duration, 1 / fs)
    real_hr = 72                   # 模拟真实心率 72
    wave = (np.sin(2 * np.pi * (real_hr / 60) * t)
            + 0.3 * np.sin(2 * np.pi * 0.5 * t))
    peaks, _ = find_peaks(wave, distance=fs * 0.4)
    return len(peaks) * 60 / duration   # 次数 → 每分钟心率

# ---- 患者档案（病历）----
patient = {
    "姓名": "张三",
    "年龄": 68,
    "冠心病": True,
    "糖尿病": False,
    "肾功能不全": False,
    "病情不稳定": False,
    "收缩压": 158,          # 来自病历
}

# ============================================================
# Agent 主流程（每一步都打印日志，演示时观众能看懂"它干了什么"）
# ============================================================
print("=" * 56)
print("PeriRisk Agent 开始术前风险评估")
print("=" * 56)

# [1/4] 信号处理：波形 → 心率
print("[1/4] 信号处理：读取监护波形 → 检测心跳 → 计算心率")
hr = compute_hr_from_wave()
print(f"      ✓ 完成：估算心率 {hr:.0f} 次/分钟")

# [2/4] 规则评分：病历 + 心率 → ASA 分级
print("[2/4] 规则评分：根据病历计算 ASA 分级")
grade = assess_asa(
    patient["年龄"],
    patient["冠心病"],
    patient["糖尿病"],
    patient["肾功能不全"],
    patient["病情不稳定"],
)
print(f"      ✓ 完成：ASA {grade}")

# [3/4] 整理患者摘要（把上面算出的结果拼成一段话）
print("[3/4] 整理患者摘要")
summary = (
    f"患者{patient['姓名']}，{patient['年龄']}岁，"
    f"ASA分级（程序计算）：{grade}，"
    f"心率 {hr:.0f} 次/分钟（由监护波形自动计算），"
    f"收缩压 {patient['收缩压']} mmHg，"
    f"既往史：冠心病{'是' if patient['冠心病'] else '否'}、"
    f"糖尿病{'是' if patient['糖尿病'] else '否'}。"
)
print(f"      ✓ 摘要：{summary}")

# [4/4] 大模型：根据摘要生成专业报告
print("[4/4] 调用大模型生成风险评估报告…")
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
print("PeriRisk Agent 评估完成")
