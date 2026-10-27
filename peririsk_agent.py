# ============================================================
# PeriRisk Demo · 第 6 步：Agent 版 —— DeepSeek 自主调度工具
# 和流水线版的本质区别：
#   流水线 —— 剧本写死：算心率 → 算分级 → 拼摘要 → 出报告
#   Agent —— 只给大脑一个"工具箱"和任务，它自己决定先查什么、后查什么，
#            每轮把工具结果喂回去，直到它认为信息够了再写报告。
# 工具实现、JSON Schema 和工具注册表都在 tools/ 包；
# 本文件只保留 Agent 主循环：
# 思考 → 点名工具 → 本地执行 → 结果回填 → 再思考（run_agent）
# 用法：python peririsk_agent.py
# ============================================================

import json
import os
import sys
import threading
import time

from llm import chat_with_tools
from runtime_state import set_patient
from tools import TOOL_FUNCTIONS, TOOLS

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
# Agent 主循环
# ============================================================

SYSTEM_PROMPT = (
    "你是术前风险评估协调员。请按需调用工具收集信息："
    "① 查病历；② 分析监护波形得到心率；③ 计算 ASA 分级。"
    "信息收集齐后，停止调用工具，直接输出一份术前风险评估报告，"
    "格式包含三部分：【风险评估】【麻醉关注点】【建议】。\n"
    "数据引用规则（必须严格遵守）：\n"
    "1. 报告中【每一条结论】的句末，都要用括号附上它实际引用的工具返回值，例如："
    "（依据：病历工具返回 年龄68岁、收缩压158mmHg；心率工具返回 算法心率87.0次/分、PLETH_HR87.8次/分；"
    "ASA规则引擎判定 III级）。\n"
    "2. 依据只能来自本次工具调用在对话中真实返回的字段，数值逐字照抄，"
    "禁止编造、推测或引用任何工具没有返回的信息。注意：结论正文和依据里都不许出现"
    "工具未返回的信息——工具不返回性别（绝不能写\"男性/女性\"）、舒张压、高血压诊断、"
    "冠脉造影结果等，这些一律不能写。布尔值一律写成\"有/无\"或\"是/否\"，"
    "不要直接出现 true/false 字样。\n"
    "3. 三个工具返回的字段仅限于："
    "病历工具 get_patient_record（姓名、年龄、冠心病、糖尿病、肾功能不全、病情不稳定、收缩压、波形ID）；"
    "心率工具 analyze_waveform（波形ID、分析时长秒、参考窗口秒、检测心跳次数、算法心率、PLETH_HR、HR、监护仪对照心率）；"
    "ASA规则引擎 assess_asa_grade（ASA分级）。\n"
    "4. 某条结论找不到工具返回值支撑，就不要写这条结论；工具没返回的信息不要出现在依据里。\n"
    "5. 三段式结构和现有措辞风格保持不变，只在每条结论句末补括号依据，不要单独罗列数据清单。\n"
    "6. 调用 analyze_waveform 时，先使用病历工具返回的波形ID；除非用户明确要求比较不同窗口，否则 segment_seconds 固定传 60。"
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
