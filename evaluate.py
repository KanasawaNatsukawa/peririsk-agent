# ============================================================
# PeriRisk Demo · 离线批量评估脚本（独立，不改主程序）
# 对一组测试病例真实跑 Agent，逐项体检：
#   ① 工具调用顺序对不对（查病历 → 心率检测 → ASA 分级）
#   ② Agent 拿到的 ASA 分级，和规则引擎直接算的是否一致
#      （工具内部就是同一个 assess_asa；不一致只可能是大模型传错了病历参数）
#   ③ 算法心率与监护仪参考心率的绝对误差
# 结果：控制台汇总表 + evaluation_results.csv
# 用法：python evaluate.py
# ============================================================

import argparse
import csv
import itertools
import statistics
import sys
import unicodedata
from pathlib import Path

import patient
import peririsk_agent as agent
from peririsk_agent import run_agent
from patient import EVALUATION_CASES, assess_patient
from tools.waveform import (
    _load_case_data,
    compare_selection_policies,
    evaluate_window_candidates,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---- 测试病例：统一从 patient.py 的病例花名册读取 ----
TEST_CASES = [
    {**档案, "_标签": 标签}
    for 标签, 档案 in EVALUATION_CASES
]

WINDOW_RESULTS_FILE = "window_evaluation_results.csv"
WINDOW_SUMMARY_FILE = "window_evaluation_summary.csv"
WINDOW_POLICY_FILE = "window_policy_comparison.csv"
PARAMETER_SEARCH_FILE = "heart_rate_parameter_search.csv"

# 工具内部名 → 表格里显示的短名
TOOL_CN = {
    "get_patient_record": "病历",
    "validate_case_data": "数据质量",
    "analyze_waveform": "心率",
    "compare_hr_windows": "稳定性",
    "assess_asa_grade": "ASA",
}


def _rounded_mean(values):
    return round(statistics.mean(values), 1) if values else ""


def _rounded_median(values):
    return round(statistics.median(values), 1) if values else ""


def evaluate_all_windows(output_dir="."):
    """确定性评估 5 个病例的全部候选 60 秒窗口，不调用大模型。"""
    all_rows = []
    summaries = []
    policy_rows = []
    all_same_diffs = []
    all_cross_diffs = []

    for patient_label, profile in patient.PATIENTS.items():
        waveform_id = patient.PATIENT_WAVEFORMS[profile["姓名"]]
        pleth, numeric_rows = _load_case_data(waveform_id)
        evaluation = evaluate_window_candidates(
            pleth,
            numeric_rows=numeric_rows,
            window_seconds=60,
        )
        candidates = evaluation["候选窗口"]
        selected = candidates[0]
        same_diffs = [float(item["同源差"]) for item in candidates]
        cross_diffs = [float(item["综合HR差"]) for item in candidates]
        all_same_diffs.extend(same_diffs)
        all_cross_diffs.extend(cross_diffs)
        for policy in compare_selection_policies(candidates):
            policy_rows.append({
                "病例": patient_label,
                "姓名": profile["姓名"],
                "波形ID": waveform_id,
                **policy,
            })
        same_error_rank = sorted(
            candidates,
            key=lambda item: (item["同源差"], item["综合HR差"], item["起始秒"]),
        ).index(selected) + 1

        for candidate in candidates:
            all_rows.append({
                "病例": patient_label,
                "姓名": profile["姓名"],
                "波形ID": waveform_id,
                "窗口起始秒": candidate["起始秒"],
                "窗口结束秒": candidate["结束秒"],
                "是否选中": "是" if candidate["是否选中"] else "否",
                "质量排名": candidate["质量排名"],
                "有效采样点比例": candidate["有效采样点比例"],
                "异常采样点": candidate["异常采样点"],
                "幅度哨兵点": candidate["幅度哨兵点"],
                "波形峰峰值": candidate["波形峰峰值"],
                "前半段心率": candidate["前半段心率"],
                "后半段心率": candidate["后半段心率"],
                "前后半段心率差": candidate["前后半段心率差"],
                "检测心跳次数": candidate["检测心跳次数"],
                "算法心率": candidate["算法心率"],
                "PLETH_HR": candidate["PLETH_HR"],
                "HR": candidate["HR"],
                "同源差": candidate["同源差"],
                "综合HR差": candidate["综合HR差"],
            })

        summaries.append({
            "病例": patient_label,
            "姓名": profile["姓名"],
            "波形ID": waveform_id,
            "候选窗口数": len(candidates),
            "选中起始秒": selected["起始秒"],
            "选中结束秒": selected["结束秒"],
            "选中算法心率": selected["算法心率"],
            "选中同源差": selected["同源差"],
            "选中综合HR差": selected["综合HR差"],
            "全窗同源均值": _rounded_mean(same_diffs),
            "全窗同源中位数": _rounded_median(same_diffs),
            "全窗同源最大差": round(max(same_diffs), 1),
            "全窗综合HR均值": _rounded_mean(cross_diffs),
            "全窗综合HR中位数": _rounded_median(cross_diffs),
            "全窗综合HR最大差": round(max(cross_diffs), 1),
            "选中同源差排名(仅评估)": same_error_rank,
        })

    summaries.append({
        "病例": "全部病例",
        "姓名": "",
        "波形ID": "",
        "候选窗口数": len(all_rows),
        "选中起始秒": "",
        "选中结束秒": "",
        "选中算法心率": "",
        "选中同源差": _rounded_mean([
            float(item["选中同源差"]) for item in summaries
        ]),
        "选中综合HR差": _rounded_mean([
            float(item["选中综合HR差"]) for item in summaries
        ]),
        "全窗同源均值": _rounded_mean(all_same_diffs),
        "全窗同源中位数": _rounded_median(all_same_diffs),
        "全窗同源最大差": round(max(all_same_diffs), 1),
        "全窗综合HR均值": _rounded_mean(all_cross_diffs),
        "全窗综合HR中位数": _rounded_median(all_cross_diffs),
        "全窗综合HR最大差": round(max(all_cross_diffs), 1),
        "选中同源差排名(仅评估)": "",
    })

    policy_summary = []
    for policy_name in (
        "固定首窗",
        "仅信号质量",
        "质量+稳定性",
        "参考最优",
    ):
        items = [
            item for item in policy_rows
            if item["策略"] == policy_name
        ]
        same_diffs = [float(item["同源差"]) for item in items]
        cross_diffs = [float(item["综合HR差"]) for item in items]
        policy_summary.append({
            "策略": policy_name,
            "病例数": len(items),
            "同源差均值": _rounded_mean(same_diffs),
            "同源差中位数": _rounded_median(same_diffs),
            "同源差最大": round(max(same_diffs), 1),
            "综合HR差均值": _rounded_mean(cross_diffs),
            "综合HR差中位数": _rounded_median(cross_diffs),
            "综合HR差最大": round(max(cross_diffs), 1),
            "使用参考心率选窗": (
                "是" if policy_name == "参考最优" else "否"
            ),
        })

    output_path = Path(output_dir)
    results_path = output_path / WINDOW_RESULTS_FILE
    summary_path = output_path / WINDOW_SUMMARY_FILE
    policy_path = output_path / WINDOW_POLICY_FILE

    with open(results_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=all_rows[0].keys())
        writer.writeheader()
        writer.writerows(all_rows)

    with open(summary_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=summaries[0].keys())
        writer.writeheader()
        writer.writerows(summaries)

    with open(policy_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=policy_rows[0].keys())
        writer.writeheader()
        writer.writerows(policy_rows)

    print("\n" + "=" * 88)
    print("  PeriRisk 全候选窗口评估（不调用大模型）")
    print("=" * 88)
    table = [[
        "病例",
        "选中窗口",
        "算法HR",
        "同源差",
        "综合HR差",
        "全窗同源均值",
        "全窗同源最差",
        "同源误差排名",
    ]]
    for item in summaries[:-1]:
        table.append([
            item["波形ID"],
            f"{item['选中起始秒']}–{item['选中结束秒']}",
            str(item["选中算法心率"]),
            str(item["选中同源差"]),
            str(item["选中综合HR差"]),
            str(item["全窗同源均值"]),
            str(item["全窗同源最大差"]),
            str(item["选中同源差排名(仅评估)"]),
        ])
    print_table(table)
    overall = summaries[-1]
    print("-" * 88)
    print(f"候选窗口总数：{overall['候选窗口数']}")
    print(
        "全部候选同源差："
        f"均值 {overall['全窗同源均值']}，"
        f"中位数 {overall['全窗同源中位数']}，"
        f"最大 {overall['全窗同源最大差']} 次/分"
    )
    print(
        "全部候选综合HR差："
        f"均值 {overall['全窗综合HR均值']}，"
        f"中位数 {overall['全窗综合HR中位数']}，"
        f"最大 {overall['全窗综合HR最大差']} 次/分"
    )
    policy_table = [[
        "策略",
        "同源均值",
        "同源中位数",
        "同源最差",
        "综合HR均值",
        "综合HR最差",
        "使用参考",
    ]]
    for item in policy_summary:
        policy_table.append([
            item["策略"],
            str(item["同源差均值"]),
            str(item["同源差中位数"]),
            str(item["同源差最大"]),
            str(item["综合HR差均值"]),
            str(item["综合HR差最大"]),
            item["使用参考心率选窗"],
        ])
    print("\n选窗策略对比：")
    print_table(policy_table)
    print(f"明细已导出：{results_path}")
    print(f"汇总已导出：{summary_path}")
    print(f"策略对比已导出：{policy_path}")
    return all_rows, summaries, policy_rows, policy_summary


def search_heart_rate_parameters(
    prominences=None,
    min_distances=None,
    output_dir=".",
):
    """按全部候选窗口评估 prominence × distance 参数网格。"""
    prominences = prominences or [round(0.1 * i, 1) for i in range(1, 11)]
    min_distances = min_distances or [0.3, 0.4, 0.5, 0.6]
    case_data = []
    for patient_label, profile in patient.PATIENTS.items():
        waveform_id = patient.PATIENT_WAVEFORMS[profile["姓名"]]
        pleth, numeric_rows = _load_case_data(waveform_id)
        case_data.append((
            patient_label,
            profile,
            waveform_id,
            pleth,
            numeric_rows,
        ))

    rows = []
    for prominence, min_distance in itertools.product(
        prominences,
        min_distances,
    ):
        all_same_diffs = []
        all_cross_diffs = []
        selected_same_diffs = []
        selected_cross_diffs = []

        for _, _, _, pleth, numeric_rows in case_data:
            evaluation = evaluate_window_candidates(
                pleth,
                numeric_rows=numeric_rows,
                window_seconds=60,
                prominence=prominence,
                min_distance_seconds=min_distance,
            )
            candidates = evaluation["候选窗口"]
            all_same_diffs.extend(float(item["同源差"]) for item in candidates)
            all_cross_diffs.extend(float(item["综合HR差"]) for item in candidates)
            selected = candidates[0]
            selected_same_diffs.append(float(selected["同源差"]))
            selected_cross_diffs.append(float(selected["综合HR差"]))

        same_mean = statistics.mean(all_same_diffs)
        same_median = statistics.median(all_same_diffs)
        same_max = max(all_same_diffs)
        cross_mean = statistics.mean(all_cross_diffs)
        selected_same_mean = statistics.mean(selected_same_diffs)
        selected_cross_mean = statistics.mean(selected_cross_diffs)
        robust_score = (
            same_mean
            + 0.5 * same_max
            + 0.25 * cross_mean
            + 0.25 * selected_same_mean
            + 0.15 * selected_cross_mean
        )
        rows.append({
            "prominence": prominence,
            "min_distance_seconds": min_distance,
            "候选窗口数": len(all_same_diffs),
            "全窗同源均值": round(same_mean, 3),
            "全窗同源中位数": round(same_median, 3),
            "全窗同源最大差": round(same_max, 3),
            "同源差≤3比例": round(
                sum(value <= 3 for value in all_same_diffs)
                / len(all_same_diffs),
                3,
            ),
            "全窗综合HR均值": round(cross_mean, 3),
            "全窗综合HR中位数": round(
                statistics.median(all_cross_diffs),
                3,
            ),
            "全窗综合HR最大差": round(max(all_cross_diffs), 3),
            "选中窗口同源均值": round(
                selected_same_mean,
                3,
            ),
            "选中窗口综合HR均值": round(
                selected_cross_mean,
                3,
            ),
            "稳健评分": round(robust_score, 3),
        })

    rows.sort(
        key=lambda item: (
            item["稳健评分"],
            abs(item["prominence"] - 0.5),
            abs(item["min_distance_seconds"] - 0.4),
        )
    )
    for rank, row in enumerate(rows, 1):
        row["综合排名"] = rank

    output_path = Path(output_dir) / PARAMETER_SEARCH_FILE
    fieldnames = ["综合排名"] + [
        key for key in rows[0].keys()
        if key != "综合排名"
    ]
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\n" + "=" * 88)
    print("  心率检测参数网格搜索（基于全部候选窗口）")
    print("=" * 88)
    table = [[
        "排名",
        "prominence",
        "distance",
        "同源均值",
        "同源中位数",
        "同源最差",
        "≤3比例",
        "综合HR均值",
        "稳健评分",
    ]]
    for row in rows[:10]:
        table.append([
            str(row["综合排名"]),
            str(row["prominence"]),
            str(row["min_distance_seconds"]),
            str(row["全窗同源均值"]),
            str(row["全窗同源中位数"]),
            str(row["全窗同源最大差"]),
            f"{row['同源差≤3比例']:.0%}",
            str(row["全窗综合HR均值"]),
            str(row["稳健评分"]),
        ])
    print_table(table)
    print(
        "稳健评分 = 全窗同源均值 + 0.5 × 全窗同源最差 + "
        "0.25 × 全窗综合HR均值 + 0.25 × 选中窗口同源均值 + "
        "0.15 × 选中窗口综合HR均值"
    )
    print(f"完整结果已导出：{output_path}")
    return rows


class Trace:
    """通过 on_event 回调记录一次 Agent 运行的完整轨迹（不改主循环）。

    记录：每次工具调用的先后位置（轮次, 序号）、ASA 工具的返回、心率工具的返回。
    """

    def __init__(self):
        self.calls = []          # [(轮次, 全局序号, 工具名)]
        self.asa_grades = []     # ASA 工具每次返回的分级
        self.wave_results = []   # 心率工具每次返回的结果 dict
        self.report_checks = []  # 程序化报告校验事件
        self._round = 0
        self._seq = 0

    def __call__(self, ev):
        if ev["type"] == "round":
            self._round = ev["round_no"]
        elif ev["type"] == "tool_call":
            self.calls.append((self._round, self._seq, ev["name"]))
            self._seq += 1
        elif ev["type"] == "tool_result":
            if ev["name"] == "assess_asa_grade":
                self.asa_grades.append(ev["result"].get("ASA分级", ""))
            elif ev["name"] == "analyze_waveform":
                self.wave_results.append(ev["result"])
        elif ev["type"] == "report_validation":
            self.report_checks.append(ev)


def short_grade(grade):
    """把 'III 级（重度系统性疾病，活动受限）' 缩成 'III 级'，表格才放得下。"""
    return grade.split("（")[0].strip() if grade else "—"


def judge_order(calls):
    """判断工具调用顺序是否正确，返回 (是否正确, 顺序描述串)。

    规则：病历、数据质量、心率和 ASA 必须调用；稳定性复核可选。
    病历在数据质量和心率之前，数据质量在心率之前，心率不晚于 ASA。
    """
    first = {}
    for rnd, seq, name in calls:
        if name not in first:
            first[name] = (rnd, seq)
    required = (
        "get_patient_record",
        "validate_case_data",
        "analyze_waveform",
        "assess_asa_grade",
    )
    order_desc = "缺失工具"
    ok = False
    if all(name in first for name in required):
        # 按第一次出现的位置排序，稳定性复核可以穿插在心率与 ASA 之间。
        order_desc = "→".join(
            f"{TOOL_CN.get(name, name)}(R{rnd})"
            for (rnd, seq), name in sorted(
                ((pos, name) for name, pos in first.items()),
                key=lambda x: x[0],
            )
        )
        ok = (
            first["get_patient_record"] < first["validate_case_data"]
            and first["get_patient_record"] < first["analyze_waveform"]
            and first["validate_case_data"] < first["analyze_waveform"]
            and first["get_patient_record"] < first["assess_asa_grade"]
            and first["analyze_waveform"] <= first["assess_asa_grade"]
        )
    return ok, order_desc


# ---- 控制台表格的小工具：中文字符按两个位置宽，表格才能对齐 ----
def _width(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(s))


def _pad(s, width):
    s = str(s)
    return s + " " * max(0, width - _width(s))


def print_table(rows):
    """rows: list[list[str]]，第一行是表头。按显示宽度自动对齐。"""
    cols = len(rows[0])
    widths = [max(_width(r[c]) for r in rows) for c in range(cols)]
    for i, row in enumerate(rows):
        line = "  ".join(_pad(row[c], widths[c]) for c in range(cols))
        print(line)
        if i == 0:
            print("  ".join("-" * widths[c] for c in range(cols)))


def main():
    results = []
    total = len(TEST_CASES)
    for i, case in enumerate(TEST_CASES, 1):
        label = case["_标签"]
        print(f"[{i}/{total}] 正在评估：{label}（{case['姓名']}）…")
        # 换患者：开跑前更新运行时状态，工具从 runtime_state 读取
        current_patient = {k: v for k, v in case.items() if not k.startswith("_")}
        agent.set_patient(current_patient)

        trace = Trace()
        _, rounds = run_agent(
            "请为下一位患者完成术前风险评估并输出报告。",
            on_event=trace,
        )

        # ① 调用顺序
        order_ok, order_desc = judge_order(trace.calls)
        # ② ASA：规则引擎直接算（基准） vs Agent 通过工具实际拿到的（取最后一次，即它最终采信的）
        expected = assess_patient(current_patient)
        actual = trace.asa_grades[-1] if trace.asa_grades else ""
        grade_ok = (actual == expected)
        # ③ 心率差异：取第一次心率检测；优先用同源 PLETH_HR，另记综合 HR
        if trace.wave_results:
            w = trace.wave_results[0]
            waveform_id = w.get("波形ID", "")
            window_start = w.get("分析窗口起始秒", "")
            window_end = w.get("分析窗口结束秒", "")
            hr_algo = w.get("算法心率")
            hr_ref = w.get("PLETH_HR", w.get("监护仪对照心率"))
            hr_combined = w.get("HR", "")
            hr_err = round(abs(hr_algo - hr_ref), 1) if hr_algo is not None and hr_ref is not None else ""
            hr_combined_err = (
                round(abs(hr_algo - hr_combined), 1)
                if hr_algo is not None and hr_combined != "" else ""
            )
        else:
            waveform_id = ""
            window_start = window_end = ""
            hr_algo = hr_ref = hr_combined = hr_err = hr_combined_err = ""

        report_passed = bool(
            trace.report_checks
            and trace.report_checks[-1].get("passed")
        )
        results.append({
            "标签": label,
            "姓名": case["姓名"],
            "年龄": case["年龄"],
            "波形ID": waveform_id,
            "窗口起始秒": window_start,
            "窗口结束秒": window_end,
            "预期ASA": expected,
            "Agent_AS_A": actual,
            "分级一致": grade_ok,
            "调用顺序": order_desc,
            "顺序正确": order_ok,
            "算法心率": hr_algo,
            "参考心率": hr_ref,
            "心率误差": hr_err,
            "综合HR": hr_combined,
            "综合HR差": hr_combined_err,
            "报告校验通过": report_passed,
            "报告校验重试次数": max(0, len(trace.report_checks) - 1),
            "轮数": rounds,
        })

    # ---- 汇总统计 ----
    grade_rate = sum(r["分级一致"] for r in results) / len(results)
    order_rate = sum(r["顺序正确"] for r in results) / len(results)
    hr_errs = [r["心率误差"] for r in results if r["心率误差"] != ""]
    combined_errs = [r["综合HR差"] for r in results if r["综合HR差"] != ""]
    avg_hr_err = round(sum(hr_errs) / len(hr_errs), 1) if hr_errs else 0
    avg_combined_err = round(sum(combined_errs) / len(combined_errs), 1) if combined_errs else 0
    report_pass_rate = sum(r["报告校验通过"] for r in results) / len(results)

    # ---- 控制台汇总表 ----
    print("\n" + "=" * 72)
    print("  PeriRisk Agent 离线批量评估汇总")
    print("=" * 72)
    table = [["病例", "波形", "窗口", "预期分级", "Agent分级", "一致", "调用顺序", "顺序", "同源差", "HR差", "校验", "轮数"]]
    for r in results:
        table.append([
            r["标签"],
            r["波形ID"],
            f"{r['窗口起始秒']}–{r['窗口结束秒']}" if r["窗口起始秒"] != "" else "—",
            short_grade(r["预期ASA"]),
            short_grade(r["Agent_AS_A"]),
            "✓" if r["分级一致"] else "✗",
            r["调用顺序"],
            "✓" if r["顺序正确"] else "✗",
            f"{r['心率误差']}" if r["心率误差"] != "" else "—",
            f"{r['综合HR差']}" if r["综合HR差"] != "" else "—",
            "✓" if r["报告校验通过"] else "✗",
            str(r["轮数"]),
        ])
    print_table(table)
    print("-" * 72)
    print(f"分级一致率：{sum(r['分级一致'] for r in results)}/{len(results)} = {grade_rate:.0%}")
    print(f"调用顺序正确率：{sum(r['顺序正确'] for r in results)}/{len(results)} = {order_rate:.0%}")
    print(f"报告程序校验通过率：{sum(r['报告校验通过'] for r in results)}/{len(results)} = {report_pass_rate:.0%}")
    print(f"平均同源差异（算法 vs PLETH_HR）：{avg_hr_err} 次/分（基于 {len(hr_errs)} 例）")
    print(f"平均综合 HR 差异：{avg_combined_err} 次/分（基于 {len(combined_errs)} 例）")

    # ---- 导出 CSV（utf-8-sig 带 BOM，Excel 直接打开不乱码）----
    out = "evaluation_results.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "病例", "姓名", "年龄", "波形ID", "分析窗口起始秒", "分析窗口结束秒",
            "预期ASA分级(规则引擎直算)", "Agent工具ASA分级", "分级是否一致",
            "工具调用顺序", "顺序是否正确",
            "算法心率(次/分)", "PLETH_HR同源参考(次/分)", "同源绝对差(次/分)",
            "综合HR(次/分)", "综合HR绝对差(次/分)",
            "报告程序校验是否通过", "报告校验重试次数",
            "思考轮数",
        ])
        for r in results:
            w.writerow([
                r["标签"], r["姓名"], r["年龄"], r["波形ID"],
                r["窗口起始秒"], r["窗口结束秒"],
                r["预期ASA"], r["Agent_AS_A"], "是" if r["分级一致"] else "否",
                r["调用顺序"], "是" if r["顺序正确"] else "否",
                r["算法心率"], r["参考心率"], r["心率误差"],
                r["综合HR"], r["综合HR差"],
                "是" if r["报告校验通过"] else "否",
                r["报告校验重试次数"],
                r["轮数"],
            ])
        w.writerow([])
        w.writerow(["统计", f"分级一致率 {grade_rate:.0%}",
                    f"调用顺序正确率 {order_rate:.0%}",
                    f"报告程序校验通过率 {report_pass_rate:.0%}",
                    f"平均同源差异 {avg_hr_err} 次/分",
                    f"平均综合HR差异 {avg_combined_err} 次/分"])
    print("-" * 72)
    print(f"结果已导出：{out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PeriRisk 批量评估")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--windows-only",
        action="store_true",
        help="只评估全部候选窗口，不调用 DeepSeek",
    )
    mode.add_argument(
        "--tune-heart-rate",
        action="store_true",
        help="在全部候选窗口上搜索心率检测参数，不调用 DeepSeek",
    )
    args = parser.parse_args()
    if args.windows_only:
        evaluate_all_windows()
    elif args.tune_heart_rate:
        search_heart_rate_parameters()
    else:
        main()
