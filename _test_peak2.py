# 验证 v2：阈值法峰检测（纯标准库）
import csv

WAVE = r"E:\数字孪生\python\waveform_120s.csv"
fs = 500
N = fs * 30  # 前 30 秒

pleth = []
with open(WAVE, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        pleth.append(float(row["PLETH(a.u.)"]))

sig = pleth[:N]
mean = sum(sig) / len(sig)
std = (sum((v - mean) ** 2 for v in sig) / len(sig)) ** 0.5

threshold = mean + 0.8 * std          # 只找明显高于平均的区域
min_gap = int(fs * 0.4)               # 两次心跳至少隔 0.4 秒

# 找出所有"高于阈值"的连续区域，每段取最高点作为心跳
peaks = []
in_seg = False
seg_start = 0
seg_max_i = 0
seg_max_v = -1e9
for i, v in enumerate(sig):
    if v > threshold:
        if not in_seg:
            in_seg = True
            seg_start = i
            seg_max_i, seg_max_v = i, v
        elif v > seg_max_v:
            seg_max_i, seg_max_v = i, v
    else:
        if in_seg:
            in_seg = False
            # 段长 < 0.4 秒可能只是毛刺，但相邻两段若太近也算同一次心跳
            if not peaks or (seg_max_i - peaks[-1]) >= min_gap:
                peaks.append(seg_max_i)

hr = len(peaks) * 60 / 30
print(f"阈值={threshold:.1f}  检测到 {len(peaks)} 次心跳，估算心率 {hr:.0f} 次/分钟")
