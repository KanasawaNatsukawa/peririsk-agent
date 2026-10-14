# 验证：120 秒波形按 30 秒分段，每段心率
import csv

WAVE_FILE = r"E:\数字孪生\python\waveform_120s.csv"
fs = 500
SEG = 30

pleth = []
with open(WAVE_FILE, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        pleth.append(float(row["PLETH(a.u.)"]))

for seg_idx in range(4):
    start = seg_idx * SEG * fs
    end = start + SEG * fs
    sig = pleth[start:end]
    mean = sum(sig) / len(sig)
    std = (sum((v - mean) ** 2 for v in sig) / len(sig)) ** 0.5
    threshold = mean + 0.8 * std
    min_gap = int(fs * 0.4)

    peaks = []
    in_seg = False
    seg_max_i, seg_max_v = 0, -1e9
    for i, v in enumerate(sig):
        if v > threshold:
            if not in_seg:
                in_seg = True
                seg_max_i, seg_max_v = i, v
            elif v > seg_max_v:
                seg_max_i, seg_max_v = i, v
        else:
            if in_seg:
                in_seg = False
                if not peaks or (seg_max_i - peaks[-1]) >= min_gap:
                    peaks.append(seg_max_i)
    hr = len(peaks) * 60 / SEG
    print(f"第{seg_idx+1}段 ({start/fs:.0f}-{end/fs:.0f}s): {len(peaks)} 次心跳 -> {hr:.0f} 次/分钟")
