"""数字孪生推演舱的数据逻辑。

这里只做确定性计算，不调用大模型，便于单元测试和现场稳定演示。
"""

import numpy as np
import pandas as pd

from asa_risk import GRADE_TEXT, assess_asa
from tools.waveform import (
    FS,
    _analyze_segment,
    _clean_pleth_for_detection,
    _count_invalid_runs,
    _display_invalid_sample_mask,
    _load_case_data,
    _reference_values,
    compare_selection_policies,
    evaluate_window_candidates,
    select_best_window,
)


SCENARIOS = ("正常", "缺少收缩压", "波形平直", "心率冲突")


def _grade_level(grade_text):
    for level, text in GRADE_TEXT.items():
        if text == grade_text:
            return level
    raise ValueError(f"未知 ASA 分级：{grade_text}")


def asa_breakdown(
    patient,
    systolic_bp,
    bmi=None,
    active_malignancy=None,
    emergency_surgery=None,
    difficult_airway=None,
):
    """返回基础分级、血压地板和最终结果的解释。"""
    bmi = patient["BMI"] if bmi is None else float(bmi)
    active_malignancy = (
        patient["活动性恶性肿瘤"]
        if active_malignancy is None
        else bool(active_malignancy)
    )
    emergency_surgery = (
        patient["急诊手术"]
        if emergency_surgery is None
        else bool(emergency_surgery)
    )
    difficult_airway = (
        patient["困难气道"]
        if difficult_airway is None
        else bool(difficult_airway)
    )
    base_grade = assess_asa(
        patient["年龄"],
        patient["冠心病"],
        patient["糖尿病"],
        patient["肾功能不全"],
        patient["病情不稳定"],
        None,
    )
    base_level = _grade_level(base_grade)

    bmi_floor = 0
    bmi_reason = "BMI < 30，不抬高等级"
    if bmi >= 40:
        bmi_floor = 3
        bmi_reason = "BMI ≥ 40，简化为至少 III 级"
    elif bmi >= 30:
        bmi_floor = 2
        bmi_reason = "BMI 30–39.9，简化为至少 II 级"

    malignancy_floor = 3 if active_malignancy else 0
    malignancy_reason = (
        "存在活动性恶性肿瘤，简化为至少 III 级"
        if active_malignancy
        else "无活动性恶性肿瘤，不抬高等级"
    )

    if systolic_bp is None:
        return {
            "基础级别": base_level,
            "基础分级": base_grade,
            "血压地板": None,
            "BMI": bmi,
            "BMI地板": bmi_floor,
            "肿瘤地板": malignancy_floor,
            "活动性恶性肿瘤": active_malignancy,
            "急诊标识": "E" if emergency_surgery else "无",
            "困难气道": difficult_airway,
            "最终级别": None,
            "最终分级": "无法可靠分级",
            "解释": "缺少 ASA 规则必需的收缩压，停止给出最终分级。",
        }

    if systolic_bp >= 180:
        bp_floor = 3
        floor_reason = "收缩压 ≥ 180 mmHg"
    elif systolic_bp >= 140:
        bp_floor = 2
        floor_reason = "收缩压 140–179 mmHg"
    else:
        bp_floor = 1
        floor_reason = "收缩压 < 140 mmHg"

    final_level = max(base_level, bp_floor, bmi_floor, malignancy_floor)
    return {
        "基础级别": base_level,
        "基础分级": base_grade,
        "血压地板": bp_floor,
        "BMI": bmi,
        "BMI地板": bmi_floor,
        "肿瘤地板": malignancy_floor,
        "活动性恶性肿瘤": active_malignancy,
        "急诊标识": "E" if emergency_surgery else "无",
        "困难气道": difficult_airway,
        "最终级别": final_level,
        "最终分级": GRADE_TEXT[final_level],
        "解释": (
            f"{floor_reason}对应血压地板 {bp_floor}；"
            f"{bmi_reason}；{malignancy_reason}；"
            f"最终取 max({base_level}, {bp_floor}, {bmi_floor}, "
            f"{malignancy_floor}) = {final_level}。"
        ),
    }


def waveform_view(
    waveform_id,
    display_seconds=10,
    flatline=False,
    heart_rate_conflict=False,
):
    """构造推演舱使用的波形 DataFrame、峰值点和 60 秒摘要。"""
    pleth, numeric_rows = _load_case_data(waveform_id)
    selection = select_best_window(pleth, 60)
    window_start = selection["起始秒"]
    window_end = selection["结束秒"]
    analysis_segment = pleth[window_start * FS: window_end * FS].copy()
    display_seconds = max(5, min(int(display_seconds), 60))
    segment = analysis_segment[: FS * display_seconds].copy()
    display_invalid = _display_invalid_sample_mask(segment)
    raw_abnormal_points = int(np.count_nonzero(display_invalid))
    clean_full = _clean_pleth_for_detection(analysis_segment)
    clean_segment = clean_full[: segment.size]

    if flatline:
        finite_segment = segment[np.isfinite(segment)]
        baseline = float(np.median(finite_segment)) if finite_segment.size else 0.0
        segment = np.full_like(segment, baseline)
        clean_segment = segment.copy()
        display_invalid = np.zeros(segment.size, dtype=bool)
        peaks = np.asarray([], dtype=int)
    else:
        segment[display_invalid] = np.nan
        peaks, _ = _analyze_segment(analysis_segment, display_seconds)
        peaks = peaks[~display_invalid[peaks]]

    stride = 5  # 500 Hz 原始点降为 100 Hz 用于浏览器绘制
    sample_idx = np.arange(0, segment.size, stride)
    waveform_df = pd.DataFrame({
        "time": sample_idx / FS,
        "pleth": clean_segment[sample_idx],
    })
    peaks_df = pd.DataFrame({
        "time": peaks / FS,
        "pleth": clean_segment[peaks] if peaks.size else [],
    })
    if not flatline:
        waveform_df.loc[display_invalid[sample_idx], "pleth"] = np.nan

    full_seconds = 60
    if flatline:
        full_peaks = np.asarray([], dtype=int)
        algorithm_hr = 0.0
        quality = "不足"
        quality_issue = "模拟平直波形：无法形成可靠峰"
    else:
        full_peaks, algorithm_hr = _analyze_segment(
            analysis_segment,
            full_seconds,
        )
        if raw_abnormal_points:
            quality_issue = (
                f"检测到 {raw_abnormal_points} 个数据异常采样点"
                "（含幅度哨兵或起始基线未稳定），"
                "图中已断开异常段；心率检测仅对幅度哨兵局部插值"
            )
            quality = "警告"
        else:
            quality_issue = ""
            quality = "通过"

    ref_pleth, ref_hr = _reference_values(
        numeric_rows,
        full_seconds,
        start_seconds=window_start,
    )
    if heart_rate_conflict and not flatline:
        ref_pleth = algorithm_hr + 6

    finite_ratio = (
        float(np.isfinite(segment).sum() / segment.size)
        if segment.size else 0.0
    )
    amplitude_range = (
        float(np.ptp(clean_segment[np.isfinite(clean_segment)]))
        if np.isfinite(clean_segment).any() else 0.0
    )

    return {
        "waveform": waveform_df,
        "peaks": peaks_df,
        "波形ID": waveform_id,
        "原始数据时长秒": len(pleth) // FS,
        "工具选择起始秒": window_start,
        "工具选择结束秒": window_end,
        "候选窗口数": selection["候选窗口数"],
        "窗口选择说明": selection["选择说明"],
        "显示窗口秒": display_seconds,
        "显示窗口峰数": int(len(peaks)),
        "60秒峰数": int(len(full_peaks)),
        "算法心率": round(float(algorithm_hr), 1),
        "PLETH_HR": round(float(ref_pleth), 1),
        "HR": round(float(ref_hr), 1),
        "心率差": round(abs(algorithm_hr - ref_pleth), 1),
        "有效采样点比例": finite_ratio,
        "异常采样点": (
            int(np.count_nonzero(display_invalid)) if not flatline else 0
        ),
        "异常区间数": _count_invalid_runs(display_invalid),
        "波形峰峰值": amplitude_range,
        "波形质量": quality,
        "质量问题": quality_issue,
    }


def candidate_quality_view(waveform_id):
    """返回某个病例全部候选 60 秒窗口的质量与参考心率差异。"""
    pleth, numeric_rows = _load_case_data(waveform_id)
    evaluation = evaluate_window_candidates(
        pleth,
        numeric_rows=numeric_rows,
        window_seconds=60,
    )
    return {
        "波形ID": waveform_id,
        "原始数据时长秒": len(pleth) // FS,
        **evaluation,
        "策略对比": compare_selection_policies(evaluation["候选窗口"]),
    }


def scenario_path(scenario, conflict=False):
    """返回推演场景对应的预期工具路径。"""
    if scenario == "缺少收缩压":
        return ["get_patient_record", "validate_case_data", "停止：缺少收缩压"]
    if scenario == "波形平直":
        return ["get_patient_record", "validate_case_data", "停止：波形质量不足"]
    if conflict:
        return [
            "get_patient_record",
            "validate_case_data",
            "analyze_waveform",
            "compare_hr_windows",
            "assess_asa_grade",
        ]
    return [
        "get_patient_record",
        "validate_case_data",
        "analyze_waveform",
        "assess_asa_grade",
    ]
