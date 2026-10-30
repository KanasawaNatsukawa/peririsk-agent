# ============================================================
# PeriRisk Demo · Web 界面（Streamlit）
# 按钮下方 → "Agent 思考过程"区（灰色小字逐行，0.5 秒节奏）→ 最终报告
# 思考过程由 run_agent 的 on_event 回调实时驱动，和真实工具调用一一对应，不写死。
# 运行：streamlit run app.py  （或 python -m streamlit run app.py）
# ============================================================

import html
import time

import pandas as pd
import streamlit as st

# 直接复用 Agent 的主循环——工具、说明书、循环逻辑全在 peririsk_agent 里
import patient
import peririsk_agent as agent     # 用来在开跑前切换"当前患者"，Agent 本身一行不改
import twin_lab
from peririsk_agent import run_agent

st.set_page_config(
    page_title="PeriRisk 围术期风险评估智能体",
    page_icon="🏥",
    layout="centered",
)

# ---- 页面标题 ----
st.title("PeriRisk 围术期风险评估智能体")
st.caption("Agent 自主调度工具：查病历 → 检查数据质量 → 心率分析 → 稳定性复核 → ASA 分级")


# ---- 工具名 → 人类可读的中文动作（写进"[思考轮N] 正在…"标题）----
TOOL_DESC = {
    "get_patient_record": "查询患者病历",
    "validate_case_data": "检查病历与波形质量",
    "analyze_waveform": "分析监护波形",
    "compare_hr_windows": "比较心率窗口稳定性",
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
                f"BMI {result.get('BMI')}，"
                f"收缩压 {result.get('收缩压')} mmHg）")
    if name == "validate_case_data":
        return (
            f"数据质量 {result.get('波形质量')}，"
            f"有效采样点 {result.get('有效采样点比例', 0) * 100:.1f}%，"
            f"自动选窗 {result.get('选择窗口起始秒')}–{result.get('选择窗口结束秒')} 秒，"
            f"异常采样点 {result.get('异常采样点', 0)} 个，"
            f"可继续分析：{'是' if result.get('是否可以继续分析') else '否'}"
        )
    if name == "analyze_waveform":
        waveform_id = result.get("波形ID", "?")
        start = result.get("分析窗口起始秒", "?")
        end = result.get("分析窗口结束秒", "?")
        pleth_hr = result.get("PLETH_HR", result.get("监护仪对照心率"))
        hr = result.get("HR")
        return (f"算法心率 {result.get('算法心率')} 次/分"
                f"（{waveform_id}，自动选择 {start}–{end} 秒；PLETH_HR {pleth_hr}，"
                f"综合 HR {hr}；检测心跳 {result.get('检测心跳次数')} 次）")
    if name == "compare_hr_windows":
        return (
            f"最大心率差 {result.get('最大心率差')} 次/分，"
            f"{'稳定' if result.get('是否稳定') else '不稳定'}"
            f"（窗口 {result.get('比较窗口秒')}）")
    if name == "assess_asa_grade":
        grade = result.get("ASA分级", str(result))
        emergency = result.get("急诊标识", "无")
        airway = result.get("困难气道关注", "无")
        return f"{grade}；急诊标识 {emergency}；{airway}"
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
        elif ev["type"] == "report_validation":
            if ev["passed"]:
                thought("  ✓ 程序校验: 报告字段与依据格式通过")
            else:
                thought("  ! 程序校验发现问题，正在要求模型修正: " + "；".join(ev["issues"]))
            time.sleep(0.5)


@st.cache_data(ttl="1h", max_entries=30)
def load_twin_waveform(
    waveform_id,
    display_seconds,
    flatline,
    conflict,
    cache_version=8,
):
    return twin_lab.waveform_view(
        waveform_id,
        display_seconds=display_seconds,
        flatline=flatline,
        heart_rate_conflict=conflict,
    )


@st.cache_data(ttl="1h", max_entries=10)
def load_twin_window_quality(waveform_id, cache_version=2):
    return twin_lab.candidate_quality_view(waveform_id)


def waveform_chart(waveform_df, peaks_df):
    """构造一条可缩放的 PPG 曲线，并在本地检测峰上叠加红点。"""
    line_data = [
        [float(time_value), None if pd.isna(pleth) else float(pleth)]
        for time_value, pleth in waveform_df[["time", "pleth"]].itertuples(
            index=False,
            name=None,
        )
    ]
    peak_data = peaks_df[["time", "pleth"]].to_numpy().tolist()
    max_time = float(waveform_df["time"].max()) if not waveform_df.empty else 0.0

    return {
        "animationDuration": 500,
        "grid": {"left": 58, "right": 22, "top": 26, "bottom": 52},
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
        },
        "xAxis": {
            "type": "value",
            "name": "时间（秒）",
            "min": 0,
            "max": max_time,
            "axisLabel": {"color": "#667085"},
            "nameTextStyle": {"color": "#475467"},
            "splitLine": {"show": False},
        },
        "yAxis": {
            "type": "value",
            "name": "PLETH（a.u.）",
            "scale": True,
            "axisLabel": {"color": "#667085"},
            "nameTextStyle": {"color": "#475467"},
            "splitLine": {"lineStyle": {"color": "#EAECF0"}},
        },
        "dataZoom": [{"type": "inside", "filterMode": "none"}],
        "series": [
            {
                "name": "PPG 波形",
                "type": "line",
                "data": line_data,
                "showSymbol": False,
                "connectNulls": False,
                "sampling": "lttb",
                "lineStyle": {"color": "#2F6BFF", "width": 2},
                "itemStyle": {"color": "#2F6BFF"},
                "areaStyle": {
                    "color": {
                        "type": "linear",
                        "x": 0,
                        "y": 0,
                        "x2": 0,
                        "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "rgba(47,107,255,0.20)"},
                            {"offset": 1, "color": "rgba(47,107,255,0.01)"},
                        ],
                    }
                },
            },
            {
                "name": "检测峰",
                "type": "scatter",
                "data": peak_data,
                "symbolSize": 8,
                "itemStyle": {
                    "color": "#E45756",
                    "borderColor": "#FFFFFF",
                    "borderWidth": 1,
                },
                "z": 3,
            },
        ],
    }


def candidate_quality_heatmap(candidates):
    """构造全部候选窗口的质量热力图。"""
    candidates = sorted(candidates, key=lambda item: item["起始秒"])
    x_labels = [
        f"{item['起始秒']}–{item['结束秒']}"
        for item in candidates
    ]
    max_outliers = max((item["异常采样点"] for item in candidates), default=0)
    rows = [
        (
            "异常点数量",
            [
                100.0 if max_outliers == 0
                else 100 * (1 - item["异常采样点"] / max_outliers)
                for item in candidates
            ],
            [f"{item['异常采样点']}" for item in candidates],
        ),
        (
            "有效采样率",
            [item["有效采样点比例"] * 100 for item in candidates],
            [f"{item['有效采样点比例'] * 100:.0f}%" for item in candidates],
        ),
        (
            "前后半段心率差",
            [
                max(0.0, 100 - item["前后半段心率差"] * 10)
                for item in candidates
            ],
            [f"{item['前后半段心率差']:.1f}" for item in candidates],
        ),
        (
            "同源差（仅评估）",
            [
                max(0.0, 100 - item["同源差"] * 10)
                for item in candidates
            ],
            [f"{item['同源差']:.1f}" for item in candidates],
        ),
    ]

    data = []
    for row_index, (_, scores, labels) in enumerate(rows):
        for column_index, candidate in enumerate(candidates):
            selected = candidate["是否选中"]
            data.append({
                "value": [column_index, row_index, round(scores[column_index], 1)],
                "label": {
                    "show": True,
                    "formatter": (
                        f"✓{labels[column_index]}"
                        if selected
                        else labels[column_index]
                    ),
                    "color": "#FFFFFF",
                    "fontWeight": "bold" if selected else "normal",
                },
                "itemStyle": {
                    "borderColor": "#F79009" if selected else "#FFFFFF",
                    "borderWidth": 4 if selected else 1,
                },
            })

    return {
        "animationDuration": 350,
        "grid": {"left": 126, "right": 16, "top": 16, "bottom": 72},
        "tooltip": {"show": False},
        "xAxis": {
            "type": "category",
            "data": x_labels,
            "axisLabel": {"rotate": 35, "color": "#667085"},
            "splitArea": {"show": True},
        },
        "yAxis": {
            "type": "category",
            "data": [row[0] for row in rows],
            "inverse": True,
            "axisLabel": {"color": "#475467"},
            "splitArea": {"show": True},
        },
        "visualMap": {
            "min": 0,
            "max": 100,
            "orient": "horizontal",
            "left": "center",
            "bottom": 4,
            "calculable": False,
            "text": ["好", "差"],
            "inRange": {
                "color": ["#D92D20", "#FDB022", "#D1FADF", "#12B76A"]
            },
        },
        "series": [{
            "name": "候选窗口质量",
            "type": "heatmap",
            "data": data,
            "emphasis": {
                "itemStyle": {
                    "shadowBlur": 8,
                    "shadowColor": "rgba(0,0,0,0.25)",
                }
            },
        }],
    }


def policy_comparison_chart(policies):
    """构造四种选窗策略的误差对比条形图。"""
    labels = [
        "参考最优（仅评估）"
        if item["策略"] == "参考最优"
        else item["策略"]
        for item in policies
    ]
    return {
        "animationDuration": 400,
        "grid": {"left": 116, "right": 34, "top": 38, "bottom": 28},
        "legend": {
            "top": 0,
            "data": ["同源差", "综合HR差"],
            "textStyle": {"color": "#475467"},
        },
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "xAxis": {
            "type": "value",
            "name": "次/分",
            "axisLabel": {"color": "#667085"},
            "splitLine": {"lineStyle": {"color": "#EAECF0"}},
        },
        "yAxis": {
            "type": "category",
            "data": labels,
            "inverse": True,
            "axisLabel": {"color": "#475467"},
        },
        "series": [
            {
                "name": "同源差",
                "type": "bar",
                "data": [item["同源差"] for item in policies],
                "label": {"show": True, "position": "right"},
                "itemStyle": {"color": "#2F6BFF"},
            },
            {
                "name": "综合HR差",
                "type": "bar",
                "data": [item["综合HR差"] for item in policies],
                "label": {"show": True, "position": "right"},
                "itemStyle": {"color": "#7F56D9"},
            },
        ],
    }


assessment_tab, lab_tab = st.tabs(
    ["临床评估", "数字孪生推演"],
    key="main_workspace_tab",
    on_change="rerun",
)

if assessment_tab.open:
    with assessment_tab:
        # ---- 输入区：患者 + 自然语言任务 ----
        with st.form("assessment_form", border=True):
            patient_label = st.selectbox(
                "选择评估患者",
                list(patient.PATIENTS.keys()),
                key="patient_label",
            )
            task = st.text_area(
                "评估任务",
                value="请为当前患者完成完整术前风险评估并输出报告。",
                height=110,
                max_chars=1000,
                key="agent_task",
                help=(
                    "可以输入完整评估、只计算心率、比较不同窗口等任务。"
                    "系统会按任务和数据状态决定调用哪些工具。"
                ),
            )
            submitted = st.form_submit_button(
                "开始术前风险评估",
                icon=":material/play_arrow:",
                width="stretch",
            )

        st.caption(
            "示例：只计算当前患者心率，不评估 ASA；"
            "或：完成完整术前风险评估并输出报告。"
        )

        if submitted:
            task = task.strip()
            if not task:
                st.error("请输入评估任务。")
                st.stop()

            agent.set_patient(patient.PATIENTS[patient_label])
            st.markdown(
                '<p style="color:#666666;font-size:0.9em;margin:0.6em 0 0.2em;">Agent 思考过程</p>',
                unsafe_allow_html=True,
            )
            with st.status("正在调用大模型分析…", expanded=True) as status:
                renderer = ThoughtRenderer()
                report, rounds = run_agent(task, on_event=renderer)
                thought("信息收集完毕，正在生成评估报告...")
                time.sleep(0.5)
                status.update(label="分析完成", state="complete")

            st.divider()
            st.subheader("术前风险评估报告")
            st.markdown(report)
            st.divider()
            st.success(f"评估完成（共 {rounds} 轮思考）")

if lab_tab.open:
    with lab_tab:
        st.subheader("数字孪生场景推演")
        st.caption(
            "拖动虚拟血压或注入故障，观察患者状态、ASA 分级和 Agent 工具路径如何变化。"
        )

        patient_label = st.selectbox(
            "推演患者",
            list(patient.PATIENTS.keys()),
            index=3,
            key="twin_patient_label",
        )
        selected_patient = patient.PATIENTS[patient_label]
        patient_name = selected_patient["姓名"]
        waveform_id = patient.PATIENT_WAVEFORMS[patient_name]
        baseline_bp = selected_patient["收缩压"]

        controls_left, controls_right = st.columns(2)
        with controls_left:
            display_seconds = st.segmented_control(
                "波形显示窗口",
                [5, 10, 30, 60],
                default=10,
                key="twin_display_seconds",
            ) or 10
        with controls_right:
            scenario = st.segmented_control(
                "故障注入",
                twin_lab.SCENARIOS,
                default="正常",
                key="twin_scenario",
            ) or "正常"

        missing_bp = scenario == "缺少收缩压"
        flatline = scenario == "波形平直"
        conflict = scenario == "心率冲突"

        simulated_bp = st.slider(
            "虚拟患者收缩压（mmHg）",
            min_value=80,
            max_value=220,
            value=int(baseline_bp),
            step=1,
            key=f"twin_sbp_{patient_name}",
            disabled=missing_bp,
        )
        if missing_bp:
            simulated_bp = None

        with st.expander("扩展 ASA 参数", expanded=True):
            extra_left, extra_right = st.columns(2)
            with extra_left:
                simulated_bmi = st.slider(
                    "BMI（kg/m²）",
                    min_value=16.0,
                    max_value=50.0,
                    value=float(selected_patient["BMI"]),
                    step=0.1,
                    key=f"twin_bmi_{patient_name}",
                )
                simulated_emergency = st.toggle(
                    "急诊手术（只增加 E 标识）",
                    value=bool(selected_patient["急诊手术"]),
                    key=f"twin_emergency_{patient_name}",
                )
            with extra_right:
                simulated_malignancy = st.toggle(
                    "活动性恶性肿瘤",
                    value=bool(selected_patient["活动性恶性肿瘤"]),
                    key=f"twin_malignancy_{patient_name}",
                )
                simulated_difficult_airway = st.toggle(
                    "困难气道",
                    value=bool(selected_patient["困难气道"]),
                    key=f"twin_airway_{patient_name}",
                )

        baseline = twin_lab.asa_breakdown(selected_patient, baseline_bp)
        simulated = twin_lab.asa_breakdown(
            selected_patient,
            simulated_bp,
            bmi=simulated_bmi,
            active_malignancy=simulated_malignancy,
            emergency_surgery=simulated_emergency,
            difficult_airway=simulated_difficult_airway,
        )
        wave = load_twin_waveform(
            waveform_id,
            int(display_seconds),
            flatline,
            conflict,
            cache_version=8,
        )
        window_quality = load_twin_window_quality(
            waveform_id,
            cache_version=2,
        )

        chart_col, state_col = st.columns([1.55, 1], vertical_alignment="top")
        with chart_col:
            with st.container(border=True):
                st.markdown(
                    f"**{waveform_id} · 工具选择 "
                    f"{wave['工具选择起始秒']}–{wave['工具选择结束秒']} 秒 · "
                    f"显示前 {display_seconds} 秒**"
                )
                st.caption(
                    f"从 120 秒原始数据扫描 {wave['候选窗口数']} 个候选窗口："
                    f"{wave['窗口选择说明']}。"
                )
                st.echarts_chart(
                    waveform_chart(wave["waveform"], wave["peaks"]),
                    height=330,
                    width="stretch",
                    theme=None,
                    key="twin_ppg_chart",
                    alt=(
                        f"{patient_name} 的 PPG 波形，"
                        f"显示窗口内检测到 {wave['显示窗口峰数']} 个峰"
                    ),
                )
                st.caption(
                    f"红点为当前显示窗口检测到的峰；60 秒完整窗口检测到 "
                    f"{wave['60秒峰数']} 个峰。"
                    + (
                        f" 已断开 {wave['异常采样点']} 个原始异常采样点，"
                        f"共 {wave['异常区间数']} 段。"
                        if wave["异常采样点"]
                        else " 未检测到数据异常采样点。"
                    )
                )

        with state_col:
            with st.container(border=True):
                st.markdown("**虚拟患者状态**")
                metric_a, metric_b = st.columns(2)
                metric_a.metric("算法心率", f"{wave['算法心率']:.1f}")
                metric_b.metric("监护仪心率", f"{wave['PLETH_HR']:.1f}")
                st.caption("单位：次/分 · 监护仪心率来自 PLETH_HR")
                final_grade = simulated["最终分级"]
                grade_short = final_grade.split("（", 1)[0]
                st.metric(
                    "当前 ASA",
                    grade_short,
                    delta=(
                        f"较基线提高 {simulated['最终级别'] - baseline['最终级别']} 级"
                        if simulated["最终级别"] is not None
                        and simulated["最终级别"] > baseline["最终级别"]
                        else None
                    ),
                    delta_color="inverse",
                )
                if "（" in final_grade:
                    st.caption(final_grade.split("（", 1)[1].rstrip("）"))
                additional_marks = []
                if simulated["急诊标识"] == "E":
                    additional_marks.append("急诊标识 E")
                if simulated["困难气道"]:
                    additional_marks.append("困难气道需预案")
                if additional_marks:
                    st.caption(" · ".join(additional_marks))

                if flatline:
                    st.error("波形平直：峰检测失效，完整评估应暂停。")
                elif conflict:
                    st.warning(
                        f"算法心率与模拟监护仪值相差 {wave['心率差']:.1f} 次/分，"
                        "需要触发窗口稳定性复核。"
                    )
                elif missing_bp:
                    st.error("缺少收缩压：禁止继续给出可靠 ASA 分级。")
                elif wave["波形质量"] == "警告":
                    st.warning(wave["质量问题"])
                else:
                    st.success("数据质量通过，可继续完成风险评估。")

        st.markdown("#### 选窗质量热力图")
        with st.container(border=True):
            st.caption(
                "横轴为 120 秒原始数据中的 13 个候选 60 秒窗口，"
                "绿色越深表示质量越好，黄色边框表示工具最终选择。"
                "“同源差”只用于评估展示，不参与选窗。"
            )
            st.echarts_chart(
                candidate_quality_heatmap(window_quality["候选窗口"]),
                height=350,
                width="stretch",
                theme=None,
                key="twin_window_quality_heatmap",
                alt=(
                    f"{patient_name} 的 13 个候选 PPG 分析窗口质量热力图"
                ),
            )
            quality_table = pd.DataFrame([
                {
                    "质量排名": item["质量排名"],
                    "窗口": f"{item['起始秒']}–{item['结束秒']} 秒",
                    "工具选择": "是" if item["是否选中"] else "否",
                    "异常/缺失": (
                        f"{item['异常采样点']} / {item['缺失采样点']}"
                    ),
                    "半窗心率差": item["前后半段心率差"],
                    "算法/参考心率": (
                        f"{item['算法心率']:.1f} / {item['PLETH_HR']:.1f}"
                    ),
                    "同源差": item["同源差"],
                    "综合HR差": item["综合HR差"],
                }
                for item in window_quality["候选窗口"]
            ])
            st.dataframe(
                quality_table,
                hide_index=True,
                width="stretch",
                column_config={
                    "质量排名": st.column_config.NumberColumn(
                        "质量排名",
                        format="%d",
                    ),
                    "半窗心率差": st.column_config.NumberColumn(
                        "半窗心率差",
                        format="%.1f",
                    ),
                    "同源差": st.column_config.NumberColumn(
                        "同源差",
                        format="%.1f",
                    ),
                    "综合HR差": st.column_config.NumberColumn(
                        "综合HR差",
                        format="%.1f",
                    ),
                },
                alt=f"{patient_name} 的候选窗口详细指标",
            )
            st.markdown("##### 选窗策略对比")
            policy_table = pd.DataFrame([
                {
                    "策略": (
                        "参考最优（仅评估）"
                        if item["策略"] == "参考最优"
                        else item["策略"]
                    ),
                    "窗口": f"{item['窗口起始秒']}–{item['窗口结束秒']} 秒",
                    "算法心率": item["算法心率"],
                    "PLETH_HR": item["PLETH_HR"],
                    "同源差": item["同源差"],
                    "综合HR差": item["综合HR差"],
                }
                for item in window_quality["策略对比"]
            ])
            st.echarts_chart(
                policy_comparison_chart(window_quality["策略对比"]),
                height=260,
                width="stretch",
                theme=None,
                key="twin_window_policy_chart",
                alt=f"{patient_name} 的四种选窗策略误差对比",
            )
            st.dataframe(
                policy_table,
                hide_index=True,
                width="stretch",
                column_config={
                    "算法心率": st.column_config.NumberColumn(
                        "算法心率",
                        format="%.1f",
                    ),
                    "PLETH_HR": st.column_config.NumberColumn(
                        "PLETH_HR",
                        format="%.1f",
                    ),
                    "同源差": st.column_config.NumberColumn(
                        "同源差",
                        format="%.1f",
                    ),
                    "综合HR差": st.column_config.NumberColumn(
                        "综合HR差",
                        format="%.1f",
                    ),
                },
                alt=f"{patient_name} 的选窗策略明细",
            )
            st.caption(
                "“参考最优”直接使用参考答案挑窗，只用于展示理论下界，"
                "不能进入真实 Agent 策略。"
            )

        st.markdown("#### 基线状态与推演状态")
        comparison = pd.DataFrame([
            {
                "状态": "基线",
                "收缩压": f"{baseline_bp} mmHg",
                "ASA": baseline["最终分级"],
                "附加标记": (
                    f"BMI {baseline['BMI']}；"
                    f"急诊 {baseline['急诊标识']}；"
                    f"困难气道 {'有' if baseline['困难气道'] else '无'}"
                ),
                "说明": baseline["解释"],
            },
            {
                "状态": "推演",
                "收缩压": "缺失" if simulated_bp is None else f"{simulated_bp} mmHg",
                "ASA": simulated["最终分级"],
                "附加标记": (
                    f"BMI {simulated['BMI']}；"
                    f"急诊 {simulated['急诊标识']}；"
                    f"困难气道 {'有' if simulated['困难气道'] else '无'}"
                ),
                "说明": simulated["解释"],
            },
        ])
        st.dataframe(
            comparison,
            hide_index=True,
            width="stretch",
            column_config={
                "收缩压": st.column_config.TextColumn("收缩压"),
                "ASA": st.column_config.TextColumn("ASA"),
                "附加标记": st.column_config.TextColumn("附加标记"),
                "说明": st.column_config.TextColumn("因果说明", width="large"),
            },
        )

        path = twin_lab.scenario_path(scenario, conflict=conflict)
        st.markdown("#### Agent 工具路径")
        with st.container(border=True):
            st.markdown(" → ".join(f"`{step}`" for step in path))
            st.caption("该路径根据场景和数据质量变化，不是固定执行全部工具。")

        st.caption(
            "故障注入仅作用于当前页面演示，不修改病例文件；"
            "本页不是临床决策系统，ASA 仍为简化规则。"
        )
