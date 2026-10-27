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

import csv
import unicodedata

import patient
import peririsk_agent as agent
from peririsk_agent import run_agent
from patient import EVALUATION_CASES, assess_patient

# ---- 测试病例：统一从 patient.py 的病例花名册读取 ----
TEST_CASES = [
    {**档案, "_标签": 标签}
    for 标签, 档案 in EVALUATION_CASES
]

# 工具内部名 → 表格里显示的短名
TOOL_CN = {
    "get_patient_record": "病历",
    "analyze_waveform": "心率",
    "assess_asa_grade": "ASA",
}


class Trace:
    """通过 on_event 回调记录一次 Agent 运行的完整轨迹（不改主循环）。

    记录：每次工具调用的先后位置（轮次, 序号）、ASA 工具的返回、心率工具的返回。
    """

    def __init__(self):
        self.calls = []          # [(轮次, 全局序号, 工具名)]
        self.asa_grades = []     # ASA 工具每次返回的分级
        self.wave_results = []   # 心率工具每次返回的结果 dict
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


def short_grade(grade):
    """把 'III 级（重度系统性疾病，活动受限）' 缩成 'III 级'，表格才放得下。"""
    return grade.split("（")[0].strip() if grade else "—"


def judge_order(calls):
    """判断工具调用顺序是否正确，返回 (是否正确, 顺序描述串)。

    规则：三个工具都得调到；按"第一次出现的位置"，
    病历 必须在 心率、ASA 之前；心率 不晚于 ASA（同轮并行算对，因为二者都只依赖病历）。
    """
    first = {}
    for rnd, seq, name in calls:
        if name not in first:
            first[name] = (rnd, seq)
    order_desc = "缺失工具"
    ok = False
    if all(k in first for k in TOOL_CN):
        # 按第一次出现的位置排序，拼成 "病历(R1)→心率(R2)→ASA(R2)"
        order_desc = "→".join(
            f"{TOOL_CN[name]}(R{rnd})"
            for (rnd, seq), name in sorted(
                ((pos, name) for name, pos in first.items()),
                key=lambda x: x[0],
            )
        )
        ok = (
            first["get_patient_record"] < first["analyze_waveform"]
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
            hr_algo = hr_ref = hr_combined = hr_err = hr_combined_err = ""

        results.append({
            "标签": label,
            "姓名": case["姓名"],
            "年龄": case["年龄"],
            "波形ID": waveform_id,
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
            "轮数": rounds,
        })

    # ---- 汇总统计 ----
    grade_rate = sum(r["分级一致"] for r in results) / len(results)
    order_rate = sum(r["顺序正确"] for r in results) / len(results)
    hr_errs = [r["心率误差"] for r in results if r["心率误差"] != ""]
    combined_errs = [r["综合HR差"] for r in results if r["综合HR差"] != ""]
    avg_hr_err = round(sum(hr_errs) / len(hr_errs), 1) if hr_errs else 0
    avg_combined_err = round(sum(combined_errs) / len(combined_errs), 1) if combined_errs else 0

    # ---- 控制台汇总表 ----
    print("\n" + "=" * 72)
    print("  PeriRisk Agent 离线批量评估汇总")
    print("=" * 72)
    table = [["病例", "波形", "预期分级", "Agent分级", "一致", "调用顺序", "顺序", "同源差", "HR差", "轮数"]]
    for r in results:
        table.append([
            r["标签"],
            r["波形ID"],
            short_grade(r["预期ASA"]),
            short_grade(r["Agent_AS_A"]),
            "✓" if r["分级一致"] else "✗",
            r["调用顺序"],
            "✓" if r["顺序正确"] else "✗",
            f"{r['心率误差']}" if r["心率误差"] != "" else "—",
            f"{r['综合HR差']}" if r["综合HR差"] != "" else "—",
            str(r["轮数"]),
        ])
    print_table(table)
    print("-" * 72)
    print(f"分级一致率：{sum(r['分级一致'] for r in results)}/{len(results)} = {grade_rate:.0%}")
    print(f"调用顺序正确率：{sum(r['顺序正确'] for r in results)}/{len(results)} = {order_rate:.0%}")
    print(f"平均同源差异（算法 vs PLETH_HR）：{avg_hr_err} 次/分（基于 {len(hr_errs)} 例）")
    print(f"平均综合 HR 差异：{avg_combined_err} 次/分（基于 {len(combined_errs)} 例）")

    # ---- 导出 CSV（utf-8-sig 带 BOM，Excel 直接打开不乱码）----
    out = "evaluation_results.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "病例", "姓名", "年龄", "波形ID",
            "预期ASA分级(规则引擎直算)", "Agent工具ASA分级", "分级是否一致",
            "工具调用顺序", "顺序是否正确",
            "算法心率(次/分)", "PLETH_HR同源参考(次/分)", "同源绝对差(次/分)",
            "综合HR(次/分)", "综合HR绝对差(次/分)",
            "思考轮数",
        ])
        for r in results:
            w.writerow([
                r["标签"], r["姓名"], r["年龄"], r["波形ID"],
                r["预期ASA"], r["Agent_AS_A"], "是" if r["分级一致"] else "否",
                r["调用顺序"], "是" if r["顺序正确"] else "否",
                r["算法心率"], r["参考心率"], r["心率误差"],
                r["综合HR"], r["综合HR差"], r["轮数"],
            ])
        w.writerow([])
        w.writerow(["统计", f"分级一致率 {grade_rate:.0%}",
                    f"调用顺序正确率 {order_rate:.0%}",
                    f"平均同源差异 {avg_hr_err} 次/分",
                    f"平均综合HR差异 {avg_combined_err} 次/分"])
    print("-" * 72)
    print(f"结果已导出：{out}")


if __name__ == "__main__":
    main()
