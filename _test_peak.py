# 临时验证：纯标准库峰检测（不依赖 scipy/numpy）
import csv

WAVE = r"E:\数字孪生\python\waveform_120s.csv"
fs = 500
N = fs * 30  # 前 30 秒

times, pleth = [], []
with open(WAVE, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        times.append(float(row["时间(秒)"]))
        pleth.append(float(row["PLETH(a.u.)"]))

sig = pleth[:N]
min_gap = int(fs * 0.4)

# 局部极大值 + 最小间隔约束
peaks = []
prev = sig[0]
for i in range(1, len(sig) - 1):
    cur, nxt = sig[i], sig[i + 1]
    if cur > prev and cur >= nxt:  # 波峰转折点
        if not peaks or (i - peaks[-1]) >= min_gap:
            peaks.append(i)
    prev = cur

hr = len(peaks) * 60 / 30
print(f"检测到 {len(peaks)} 次心跳，估算心率 {hr:.0f} 次/分钟")
