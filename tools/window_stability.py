"""工具 5：比较多个时间窗口的心率结果，判断测量是否稳定。"""

from tools.waveform import (
    _analyze_segment,
    _clamp_segment_seconds,
    _load_case_data,
    _reference_values,
    _resolve_waveform_id,
    select_best_window,
)


SCHEMA = {
    "type": "function",
    "function": {
        "name": "compare_hr_windows",
        "description": (
            "对同一 PPG 波形分别分析多个时间窗口，返回各窗口心率、"
            "最大差值和是否稳定。用于在心率结果存疑或用户要求比较窗口时复核。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "waveform_id": {
                    "type": "string",
                    "description": "波形病例ID，使用病历工具返回的波形ID",
                },
                "windows_seconds": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "要比较的窗口秒数列表，默认 [30, 60]",
                },
                "max_difference": {
                    "type": "number",
                    "description": "判定稳定的最大允许心率差，默认 3 次/分",
                },
            },
        },
    },
}


def compare_hr_windows(
    waveform_id=None,
    windows_seconds=None,
    max_difference=3,
):
    selected_id = _resolve_waveform_id(waveform_id)
    pleth, numeric_rows = _load_case_data(selected_id)
    requested = windows_seconds or [30, 60]
    windows = sorted({
        _clamp_segment_seconds(seconds, len(pleth))
        for seconds in requested
    })
    base_seconds = max(windows)
    selection = select_best_window(pleth, base_seconds)
    start_seconds = selection["起始秒"]

    results = []
    for seconds in windows:
        peaks, hr_est = _analyze_segment(
            pleth,
            seconds,
            start_seconds=start_seconds,
        )
        ref_pleth, ref_hr = _reference_values(
            numeric_rows,
            seconds,
            start_seconds=start_seconds,
        )
        results.append({
            "窗口秒": seconds,
            "检测心跳次数": int(len(peaks)),
            "算法心率": round(hr_est, 1),
            "PLETH_HR": round(ref_pleth, 1),
            "HR": round(ref_hr, 1),
        })

    values = [item["算法心率"] for item in results]
    spread = round(max(values) - min(values), 1) if values else 0.0
    return {
        "波形ID": selected_id,
        "比较窗口起始秒": start_seconds,
        "比较窗口结束秒": start_seconds + base_seconds,
        "候选窗口数": selection["候选窗口数"],
        "选窗说明": selection["选择说明"],
        "比较窗口秒": windows,
        "各窗口结果": results,
        "最大心率差": spread,
        "稳定阈值": max_difference,
        "是否稳定": spread <= max_difference,
    }
