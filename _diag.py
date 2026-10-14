# 诊断：PLETH 波形统计特征
import csv
import statistics

WAVE = r"E:\数字孪生\python\waveform_120s.csv"
fs = 500
N = fs * 30

pleth = []
with open(WAVE, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        pleth.append(float(row["PLETH(a.u.)"]))

sig = pleth[:N]
mn, mx = min(sig), max(sig)
mean = sum(sig) / len(sig)
# 标准差
var = sum((v - mean) ** 2 for v in sig) / len(sig)
std = var ** 0.5
print(f"范围: {mn:.2f} ~ {mx:.2f}  均值: {mean:.2f}  标准差: {std:.2f}")
# 差分统计（相邻点变化幅度，噪声水平）
diffs = [abs(sig[i+1] - sig[i]) for i in range(0, len(sig)-1)]
print(f"相邻差分: 平均 {sum(diffs)/len(diffs):.4f}  最大 {max(diffs):.4f}")
# 打印前 200 个点看看波形形态
print("前 50 个点:", [round(v, 1) for v in sig[:50]])
