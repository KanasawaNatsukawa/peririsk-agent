# ============================================================
# PeriRisk Demo · 第 2 步：从波形里算出心率
# 目的：亲眼看到"信号处理"是怎么回事——给一段波形，算出心率。
# 用法：python heartbeat_demo.py
# ============================================================

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

# 让图里的中文正常显示（Windows 用微软雅黑）
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

# ---- 1) 造一段"假的脉搏波"（10 秒）----
# 真实监护仪上的脉搏波就是这样：每个凸起 = 心脏跳一下（泵血）
# 我们假设这个人真实心率 72 次/分钟 → 每秒跳 1.2 次
fs = 100                        # 采样率：每秒记录 100 个点（真实设备也差不多）
duration = 10                   # 生成 10 秒数据
t = np.arange(0, duration, 1 / fs)     # 时间轴：0 ~ 10 秒
heart_rate = 72                 # 设定的"真实心率"
beat_freq = heart_rate / 60     # 换算成每秒几次
wave = (np.sin(2 * np.pi * beat_freq * t)      # 心跳波
        + 0.3 * np.sin(2 * np.pi * 0.5 * t))   # 加一点"呼吸干扰"，更像真数据

# ---- 2) 找波峰：每个凸起的最高点 = 一次心跳 ----
peaks, _ = find_peaks(wave, distance=fs * 0.4)  # 两次心跳至少隔 0.4 秒，防止把噪声当心跳

# ---- 3) 算心率：10 秒有几次心跳 → 换算成"每分钟次数" ----
n_beats = len(peaks)
hr_estimate = n_beats * 60 / duration
print(f"10 秒内检测到 {n_beats} 次心跳 → 估算心率 {hr_estimate:.0f} 次/分钟（设定真实值 {heart_rate}）")

# ---- 4) 画图：让你"看见"波形和检测到的波峰 ----
plt.figure(figsize=(10, 4))
plt.plot(t, wave, label="脉搏波")
plt.plot(t[peaks], wave[peaks], "ro", label="检测到的心跳")
plt.xlabel("时间（秒）")
plt.ylabel("信号强度")
plt.title("脉搏波与自动心跳检测")
plt.legend()
plt.grid(True)
plt.show()
