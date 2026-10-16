# ============================================================
# PeriRisk Demo · 第 6 步：Agent 版 —— DeepSeek 自主调度工具
# 和流水线版的本质区别：
#   流水线 —— 剧本写死：算心率 → 算分级 → 拼摘要 → 出报告
#   Agent —— 只给大脑一个"工具箱"和任务，它自己决定先查什么、后查什么，
#            每轮把工具结果喂回去，直到它认为信息够了再写报告。
# 三个部件：
#   1) 工具真身：普通 Python 函数（上半部分，和 AI 无关，能单独测试）
#   2) 工具说明书：JSON Schema，告诉大脑"有什么工具、怎么用"（TOOLS）
#   3) Agent 主循环：思考 → 点名工具 → 本地执行 → 结果回填 → 再思考（run_agent）
# 用法：python peririsk_agent.py
# ============================================================

import csv
import json
import os
import sys
import threading
import time
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks

from asa_risk import assess_asa
from patient import PATIENT
from llm import chat_with_tools

# ---- 数据文件位置（跟脚本走，换电脑也能跑）----
DATA_DIR = Path(__file__).resolve().parent / "data"
WAVE_FILE = DATA_DIR / "waveform_120s.csv"
NUM_FILE = DATA_DIR / "numeric_60s.csv"

# ---- 终端着色 + loading 动画 ----
# Windows 下默认没开 ANSI 转义，调一次空命令激活 VT 处理（Win10+ 才支持彩色）
if os.name == "nt":
    os.system("")

# 颜色常量（ANSI 转义码）
BLUE = "\033[34m"      # 思考轮
YELLOW = "\033[33m"    # 调用工具
GREEN = "\033[32m"     # 工具结果
CYAN = "\033[36m"      # 标题 / 信息
BOLD = "\033[1m"
RESET = "\033[0m"


class Spinner:
    """命令行 loading 动画。包住会阻塞的调用（请求大脑、跑工具）。

    用法：
        with Spinner("正在分析波形…"):
            result = 阻塞调用()
    动画在后台线程转圈，主线程阻塞期间用户不会以为程序卡死。
    """
    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, text):
        self.text = text
        self._stop = False
        self._thread = None

    def _spin(self):
        i = 0
        while not self._stop:
            sys.stdout.write(f"\r{CYAN}{self.text} {self.FRAMES[i % len(self.FRAMES)]}{RESET}")
            sys.stdout.flush()
            time.sleep(0.08)
            i += 1
        # 退出时清掉这一行，免得和后面的输出挤在一起
        sys.stdout.write("\r" + " " * (len(self.text) + 4) + "\r")
        sys.stdout.flush()

    def __enter__(self):
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop = True
        if self._thread:
            self._thread.join()


# ============================================================
# 部件 1：工具的"真身"——普通 Python 函数
# ============================================================

def get_patient_record():
    """工具 1：查询病历。演示场景病历写死在 patient.py，真实场景来自医院 HIS。"""
    return dict(PATIENT)


def analyze_waveform(segment_seconds=30):
    """工具 2：读监护波形并检测心跳。分析多长由大脑决定（太短会不准）。"""
    pleth = []
    with open(WAVE_FILE, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            pleth.append(float(row["PLETH(a.u.)"]))
    pleth = np.array(pleth)
    fs = 500                                                # 采样率：每秒 500 点
    seconds = max(5, min(segment_seconds, len(pleth) // fs))  # 夹在 [5, 120] 秒，防乱传
    seg = pleth[: fs * seconds]
    peaks, _ = find_peaks(seg, distance=fs * 0.4, prominence=0.5)
    hr_est = len(peaks) * 60 / seconds
    hrs = []                                                # 监护仪记录的心率，做对照
    with open(NUM_FILE, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["心率(次/分)"]:
                hrs.append(float(row["心率(次/分)"]))
    ref_hr = float(np.mean(hrs))
    return {
        "分析时长秒": seconds,
        "检测心跳次数": int(len(peaks)),
        "算法心率": round(hr_est, 1),
        "监护仪对照心率": round(ref_hr, 1),
    }


def assess_asa_grade(age, coronary_heart_disease, diabetes, kidney_failure, unstable):
    """工具 3：ASA 规则引擎。参数由大脑从病历里挑出来填进去。"""
    grade = assess_asa(age, coronary_heart_disease, diabetes, kidney_failure, unstable)
    return {"ASA分级": grade}


# "电话簿"：大脑点名的名字 → 真正要执行的函数
TOOL_FUNCTIONS = {
    "get_patient_record": get_patient_record,
    "analyze_waveform": analyze_waveform,
    "assess_asa_grade": assess_asa_grade,
}


# ============================================================
# 部件 2：工具的"说明书"——JSON Schema，随请求发给大脑的"菜单"
# name / description / 参数说明写得越清楚，大脑点菜越准
# ============================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_patient_record",
            "description": "查询患者病历，返回年龄、既往史（冠心病/糖尿病/肾功能不全/病情是否稳定）和收缩压。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_waveform",
            "description": "分析监护仪脉搏波并检测心跳，返回算法心率与监护仪对照心率。建议先取 30 秒；若结果可疑可换时长重算。",
            "parameters": {
                "type": "object",
                "properties": {
                    "segment_seconds": {
                        "type": "integer",
                        "description": "分析的波形时长（秒），范围 5~120，默认 30",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "assess_asa_grade",
            "description": "根据患者情况计算 ASA 麻醉分级。调用前需要先查病历拿到各项信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "age": {"type": "integer", "description": "年龄（岁）"},
                    "coronary_heart_disease": {"type": "boolean", "description": "是否有冠心病"},
                    "diabetes": {"type": "boolean", "description": "是否有糖尿病"},
                    "kidney_failure": {"type": "boolean", "description": "是否有肾功能不全"},
                    "unstable": {"type": "boolean", "description": "病情是否不稳定"},
                },
                "required": ["age", "coronary_heart_disease", "diabetes", "kidney_failure", "unstable"],
            },
        },
    },
]


# ============================================================
# 部件 3：Agent 主循环
# ============================================================

SYSTEM_PROMPT = (
    "你是术前风险评估协调员。请按需调用工具收集信息："
    "① 查病历；② 分析监护波形得到心率；③ 计算 ASA 分级。"
    "信息收集齐后，停止调用工具，直接输出一份术前风险评估报告，"
    "格式包含三部分：【风险评估】【麻醉关注点】【建议】。"
    "必须引用工具返回的真实数值，不要编造。"
)

MAX_ROUNDS = 8   # 安全阀：防止大脑陷入死循环烧钱


def run_agent(task, on_event=None):
    """Agent 主循环。返回 (最终报告, 思考轮数)。

    on_event: 可选回调函数，每发生一件事就调一次，传一个事件 dict 进去。
      - 不传（命令行运行）→ 走原来的彩色打印 + loading 动画
      - 传了（Web 端运行）→ 改为把事件喂给界面，不在终端打印
    这样 Agent 的循环逻辑只写这一份，CLI 和 Web 共用。
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]
    for round_no in range(1, MAX_ROUNDS + 1):
        # —— 1) 通知：进入第 N 轮思考 ——
        if on_event:
            on_event({"type": "round", "round_no": round_no})
        else:
            print(f"{BLUE}{BOLD}[思考轮 {round_no}]{RESET}{BLUE} 询问大脑下一步…{RESET}")
        # —— 2) 问大脑下一步（CLI 有转圈动画，Web 端由界面自己显示进度） ——
        if on_event:
            msg = chat_with_tools(messages, TOOLS)
        else:
            with Spinner("正在询问大脑…"):
                msg = chat_with_tools(messages, TOOLS)
        calls = msg.get("tool_calls")
        if not calls:
            # 大脑不再点名工具 = 它认为信息够了，content 就是最终报告
            return msg["content"], round_no
        # API 规则：大脑的"点名单"必须原样放回对话历史，工具结果才能对上号
        messages.append(msg)
        for call in calls:
            name = call["function"]["name"]
            args = json.loads(call["function"]["arguments"] or "{}")
            # —— 3) 通知：大脑点名了工具 ——
            if on_event:
                on_event({"type": "tool_call", "name": name, "args": args})
            else:
                print(f"{YELLOW}      → 调用工具 {name}({args}){RESET}")
            try:
                if on_event:
                    result = TOOL_FUNCTIONS[name](**args)     # 真正执行的永远是我们本地
                else:
                    with Spinner(f"正在执行 {name}…"):
                        result = TOOL_FUNCTIONS[name](**args)
            except Exception as exc:                          # 出错也喂回去，让大脑自己纠错
                result = {"错误": f"{name} 执行失败：{exc}"}
            # —— 4) 通知：工具返回结果 ——
            if on_event:
                on_event({"type": "tool_result", "name": name, "result": result})
            else:
                print(f"{GREEN}      ✓ 返回：{result}{RESET}")
            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],               # 凭这个 id 和点名单对账
                "content": json.dumps(result, ensure_ascii=False),
            })
    return "（达到最大思考轮数，强制停止）", MAX_ROUNDS


def print_report(report):
    """把大脑返回的报告轻轻排版：标题着色、ASA 分级行高亮突出。

    报告是 LLM 自由生成的 markdown，逐行扫一遍：标题行青色加粗，
    含 ASA 的行黄色加粗——答辩时观众一眼就能看到分级结论。
    """
    for line in report.splitlines():
        if line.startswith("#"):
            print(f"{BOLD}{CYAN}{line}{RESET}")
        elif "ASA" in line:
            print(f"{BOLD}{YELLOW}{line}{RESET}")
        else:
            print(line)


# ============================================================
# 启动
# ============================================================
if __name__ == "__main__":
    # 命令行带提示词就用提示词，否则用默认任务，方便快速测试不同输入
    task = sys.argv[1] if len(sys.argv) > 1 else "请为下一位患者完成术前风险评估并输出报告。"
    print(f"{BOLD}{CYAN}{'═' * 56}{RESET}")
    print(f"{BOLD}{CYAN}  PeriRisk Agent（自主调度版）开始术前风险评估{RESET}")
    print(f"{CYAN}  任务：{task}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 56}{RESET}")
    report, rounds = run_agent(task)
    print(f"{BOLD}{CYAN}{'═' * 56}{RESET}")
    print(f"{BOLD}{CYAN}  术前风险评估报告（最终）{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 56}{RESET}")
    print_report(report)
    print(f"{BOLD}{CYAN}{'═' * 56}{RESET}")
    print(f"{GREEN}{BOLD}PeriRisk Agent 评估完成（共 {rounds} 轮思考）{RESET}")
