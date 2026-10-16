# ============================================================
# PeriRisk Demo · Web 界面（Streamlit）
# 把 peririsk_agent 里的 Agent 循环搬到浏览器上：
#   - 中间一个大按钮"开始术前风险评估"
#   - 点击后用 st.status 显示"正在调用大模型分析…"，并逐行追加思考过程
#     （思考轮 / 调用工具 / 返回结果，用🔵🟡🟢区分，对应 CLI 里的蓝黄绿）
#   - 最后用 markdown 渲染完整报告
# 运行：streamlit run app.py
# 依赖：streamlit（pip install streamlit）
# ============================================================

import streamlit as st

# 直接复用 Agent 的主循环——工具、说明书、循环逻辑全在 peririsk_agent 里
from peririsk_agent import run_agent

st.set_page_config(
    page_title="PeriRisk 围术期风险评估智能体",
    page_icon="🏥",
    layout="centered",
)

# ---- 页面标题 ----
st.title("PeriRisk 围术期风险评估智能体")
st.caption("Agent 自主调度工具：查病历 → 分析监护波形算心率 → 算 ASA 分级 → 大模型写报告")


# ---- 中间一个大按钮 ----
if st.button("开始术前风险评估", use_container_width=True):
    # st.status：一个可展开的状态框，自带 spinner 动画，
    # 里面 st.markdown 写的内容会逐行追加显示——正好用来直播思考过程
    with st.status("正在调用大模型分析…", expanded=True) as status:
        def on_event(ev):
            """回调：Agent 每走一步就调一次，把这一步显示到界面上。"""
            if ev["type"] == "round":
                st.markdown(f"**🔵 [思考轮 {ev['round_no']}]** 询问大脑下一步…")
            elif ev["type"] == "tool_call":
                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🟡 → 调用工具 `{ev['name']}({ev['args']})`")
            elif ev["type"] == "tool_result":
                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🟢 ✓ 返回：`{ev['result']}`")

        report, rounds = run_agent(
            "请为下一位患者完成术前风险评估并输出报告。",
            on_event=on_event,
        )
        status.update(label="分析完成", state="complete")

    # ---- 报告区：markdown 渲染，三段之间靠报告本身的空行分隔 ----
    st.divider()
    st.subheader("术前风险评估报告")
    st.markdown(report)
    st.divider()
    st.success(f"评估完成（共 {rounds} 轮思考）")
