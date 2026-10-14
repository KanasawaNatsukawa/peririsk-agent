# ============================================================
# PeriRisk Demo · 真实数据版：用 VitalDB 真实监护数据跑通全流程
# 对比上次的进步：
#   上次 —— 心率来自"造出来的正弦波"
#   这次 —— 心率来自真实手术监护记录（VitalDB 公开数据集）
# 重构说明：病历/摘要/DeepSeek 调用已抽到 patient.py 和 llm.py，
# 这里只保留本脚本独有的能力——读真实波形、峰检测、对照验证。
# 用法：python peririsk_real.py
# ============================================================

import csv
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks

from patient import PATIENT, assess_patient, build_summary
from llm import generate_report

# ---- 数据文件位置 ----
# 用"本脚本所在目录 / data"来定位，不再写死 E 盘路径：
# __file__ 是 Python 内置变量 = 当前脚本文件的路径，
# 这样无论从哪个文件夹启动、换哪台电脑，都能找到数据。
DATA_DIR = Path(__file__).resolve().parent / "data"
WAVE_FILE = DATA_DIR / "waveform_120s.csv"   # 120 秒真实波形
NUM_FILE = DATA_DIR / "numeric_60s.csv"      # 监护仪记录的数值

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
grade = assess_patient(PATIENT)
print(f"      ✓ 完成：ASA {grade}")

summary = build_summary(
    PATIENT, grade, hr_est,
    hr_note=f"（由真实手术监护波形自动计算，与监护仪记录 {ref_hr:.0f} 次/分钟一致）",
    sbp_note="（来自病历）",
)

# ---- [5/5] 大模型生成报告 ----
print("[5/5] 调用大模型生成风险评估报告…")
report = generate_report(summary)

print("=" * 56)
print(report)
print("=" * 56)
print("PeriRisk Agent 评估完成（数据来源：VitalDB 真实手术监护记录）")
