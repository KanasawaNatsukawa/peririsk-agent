# ============================================================
# PeriRisk Demo · 第 4 步（备用版）：最小可跑的主流程
# 重构说明：怎么跟 DeepSeek 说话（requests 直连、中文不卡门口）
# 已经搬进 llm.py；患者档案和摘要拼接搬进了 patient.py。
# 这个脚本只剩"流程"本身：病历 → 算分级 → 拼摘要 → 调大模型。
# 心率此处写死 92；正式流程里来自波形计算（见 peririsk_agent_final.py）
# 用法：python peririsk_agent_v1b.py
# ============================================================

from patient import PATIENT, assess_patient, build_summary
from llm import generate_report

# ---- 1) 程序算出 ASA 等级，整理成摘要 ----
grade = assess_patient(PATIENT)
summary = build_summary(PATIENT, grade, hr=92)

# ---- 2) 发给 DeepSeek，打印报告 ----
print(generate_report(summary))
