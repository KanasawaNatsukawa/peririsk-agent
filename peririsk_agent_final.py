# ============================================================
# PeriRisk Demo · 第 5 步：PeriRisk Agent 完整版（最终整合）
# 一个脚本走完 Agent 全流程：读波形 → 算心率 → 算分级 → 生成报告
# 重构说明：病历/摘要/DeepSeek 调用已抽到 patient.py 和 llm.py，
# 这里只保留本脚本独有的能力——从波形算心率 + 演示步骤日志。
# 用法：
#   1) 记事本打开 config.py，填好 key（只填一次），保存
#   2) 运行  python peririsk_agent_final.py
# ============================================================

import numpy as np
from scipy.signal import find_peaks

from patient import PATIENT, assess_patient, build_summary
from llm import generate_report

# ---- 工具：从波形算心率（信号处理能力，封装成函数）----
def compute_hr_from_wave():
    fs = 100                       # 采样率：每秒 100 个点
    duration = 10                  # 取 10 秒波形
    t = np.arange(0, duration, 1 / fs)
    real_hr = 72                   # 模拟真实心率 72
    wave = (np.sin(2 * np.pi * (real_hr / 60) * t)
            + 0.3 * np.sin(2 * np.pi * 0.5 * t))
    peaks, _ = find_peaks(wave, distance=fs * 0.4)
    return len(peaks) * 60 / duration   # 次数 → 每分钟心率


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
grade = assess_patient(PATIENT)
print(f"      ✓ 完成：ASA {grade}")

# [3/4] 整理患者摘要（把上面算出的结果拼成一段话）
print("[3/4] 整理患者摘要")
summary = build_summary(PATIENT, grade, hr, hr_note="（由监护波形自动计算）")
print(f"      ✓ 摘要：{summary}")

# [4/4] 大模型：根据摘要生成专业报告
print("[4/4] 调用大模型生成风险评估报告…")
report = generate_report(summary)

print("=" * 56)
print(report)
print("=" * 56)
print("PeriRisk Agent 评估完成")
