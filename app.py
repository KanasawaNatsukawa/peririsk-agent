# ============================================================
# PeriRisk Demo · Web 界面（Streamlit）
# 按钮下方 → "Agent 思考过程"区（灰色小字逐行，0.5 秒节奏）→ 最终报告
# 思考过程由 run_agent 的 on_event 回调实时驱动，和真实工具调用一一对应，不写死。
# 运行：streamlit run app.py  （或 python -m streamlit run app.py）
# ============================================================

import html
import time

import streamlit as st

# 直接复用 Agent 的主循环——工具、说明书、循环逻辑全在 peririsk_agent 里
import patient
import peririsk_agent as agent     # 用来在开跑前切换"当前患者"，Agent 本身一行不改
from peririsk_agent import run_agent

st.set_page_config(
    page_title="PeriRisk 围术期风险评估智能体",
    page_icon="🏥",
    layout="centered",
)

# ---- 页面标题 ----
st.title("PeriRisk 围术期风险评估智能体")
st.caption("Agent 自主调度工具：查病历 → 分析监护波形算心率 → 算 ASA 分级 → 大模型写报告")


# ---- 工具名 → 人类可读的中文动作（写进"[思考轮N] 正在…"标题）----
TOOL_DESC = {
    "get_patient_record": "查询患者病历",
    "analyze_waveform": "分析监护波形",
    "assess_asa_grade": "计算ASA麻醉分级",
}


def fmt_args(args):
    """把工具参数字典格式成 key=value 串；太长就省略，免得一行太长。"""
    if not args:
        return ""
    s = ", ".join(f"{k}={v}" for k, v in args.items())
    if len(s) > 30:
        k0, v0 = next(iter(args.items()))
        return f"{k0}={v0}, ..."
    return s


def humanize_result(name, result):
    """把工具返回的原始 dict 转成一句话，比直接打印 dict 好读。"""
    if name == "get_patient_record":
        return (f"患者信息（{result.get('年龄')}岁，"
                f"冠心病{'阳性' if result.get('冠心病') else '阴性'}，"
                f"收缩压 {result.get('收缩压')} mmHg）")
    if name == "analyze_waveform":
        return (f"算法心率 {result.get('算法心率')} 次/分"
                f"（监护仪对照 {result.get('监护仪对照心率')}，"
                f"检测心跳 {result.get('检测心跳次数')} 次）")
    if name == "assess_asa_grade":
        return result.get("ASA分级", str(result))
    return str(result)


def thought(text):
    """写一行灰色小字到界面：#666666、小一号、等宽、保留缩进。

    用 st.markdown + 内联 HTML 是为了精确控制颜色和字号
    （st.caption 做不到指定确切色值）。white-space:pre-wrap 保留"  →"的缩进。
    """
    safe = html.escape(text)
    st.markdown(
        f'<div style="color:#666666;font-size:0.88em;line-height:1.7;'
        f'white-space:pre-wrap;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;">'
        f'{safe}</div>',
        unsafe_allow_html=True,
    )


class ThoughtRenderer:
    """把 Agent 事件流渲染成灰色小字逐行的思考过程。

    每写出一条停 0.5 秒，模拟真实思考节奏。
    round 事件先缓存，等同一轮第一个工具调用来了，
    再补打"[思考轮N] 正在{动作}…"标题——这样标题能写清这轮在干嘛。
    """

    def __init__(self):
        self._pending_round = None

    def __call__(self, ev):
        if ev["type"] == "round":
            # 先攒着，等工具调用来了再决定标题写什么
            self._pending_round = ev["round_no"]
        elif ev["type"] == "tool_call":
            # 这一轮的第一个工具调用：补打带具体动作的轮次标题
            if self._pending_round is not None:
                desc = TOOL_DESC.get(ev["name"], "思考")
                thought(f"[思考轮 {self._pending_round}] 正在{desc}...")
                time.sleep(0.5)
                self._pending_round = None
            thought(f"  → 调用工具: {ev['name']}({fmt_args(ev['args'])})")
            time.sleep(0.5)
        elif ev["type"] == "tool_result":
            thought(f"  ✓ 返回: {humanize_result(ev['name'], ev['result'])}")
            time.sleep(0.5)


# ---- 患者选择：在高/低风险两个患者之间切换 ----
# 花名册（标签 → 档案卡）在 patient.py 里维护，这里只负责选
patient_label = st.selectbox("选择评估患者", list(patient.PATIENTS.keys()))

# ---- 中间一个大按钮 ----
if st.button("开始术前风险评估", use_container_width=True):
    # 把 Agent 的"查病历"工具读取的那张卡换成选中的患者。
    # 原理：get_patient_record() 内部读的是 peririsk_agent 模块里的全局 PATIENT，
    # 函数执行时才按名字查找，所以开跑前给 agent.PATIENT 赋新值就能换患者——
    # 工具定义、工具参数和 Agent 主循环一行都不用动。
    agent.PATIENT = patient.PATIENTS[patient_label]
    # 区域标题：小号灰色"Agent 思考过程"
    st.markdown(
        '<p style="color:#666666;font-size:0.9em;margin:0.6em 0 0.2em;">Agent 思考过程</p>',
        unsafe_allow_html=True,
    )
    # st.status：可展开状态框，自带 spinner 动画；expanded=True 让里面的行实时可见
    with st.status("正在调用大模型分析…", expanded=True) as status:
        renderer = ThoughtRenderer()
        report, rounds = run_agent(
            "请为下一位患者完成术前风险评估并输出报告。",
            on_event=renderer,
        )
        # run_agent 返回 = 最后一轮没再调工具，大脑直接生成报告
        thought("信息收集完毕，正在生成评估报告...")
        time.sleep(0.5)
        status.update(label="分析完成", state="complete")

    # ---- 报告区：markdown 渲染，三段之间靠报告本身的空行分隔 ----
    st.divider()
    st.subheader("术前风险评估报告")
    st.markdown(report)
    st.divider()
    st.success(f"评估完成（共 {rounds} 轮思考）")
