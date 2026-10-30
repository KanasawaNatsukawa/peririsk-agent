"""工具 4：检查当前病历与 PPG 波形是否足以继续分析。"""

import numpy as np

from runtime_state import get_patient
from tools.waveform import (
    DEFAULT_SEGMENT_SECONDS,
    FS,
    _clamp_segment_seconds,
    _clean_pleth_for_detection,
    _display_invalid_sample_mask,
    _invalid_sample_mask,
    _load_case_data,
    _resolve_waveform_id,
    select_best_window,
)


REQUIRED_PATIENT_FIELDS = (
    "姓名",
    "年龄",
    "冠心病",
    "糖尿病",
    "肾功能不全",
    "病情不稳定",
    "收缩压",
    "BMI",
    "活动性恶性肿瘤",
    "急诊手术",
    "困难气道",
)

SCHEMA = {
    "type": "function",
    "function": {
        "name": "validate_case_data",
        "description": (
            "检查当前患者病历字段是否完整，并检查绑定 PPG 波形的采样时长、"
            "缺失值、异常值、有效值比例和幅度变化，自动选择质量最好且"
            "最稳定的 60 秒窗口，判断能否继续心率与 ASA 分析。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "waveform_id": {
                    "type": "string",
                    "description": "波形病例ID，使用病历工具返回的波形ID",
                },
                "segment_seconds": {
                    "type": "integer",
                    "description": "拟检查的波形时长（5~60 秒），默认 60 秒",
                },
            },
        },
    },
}


def validate_case_data(
    waveform_id=None,
    segment_seconds=DEFAULT_SEGMENT_SECONDS,
):
    patient = get_patient()
    missing_fields = [
        field for field in REQUIRED_PATIENT_FIELDS
        if field not in patient or patient[field] in (None, "")
    ]

    selected_id = _resolve_waveform_id(waveform_id)
    pleth, _ = _load_case_data(selected_id)
    seconds = _clamp_segment_seconds(segment_seconds, len(pleth))
    selection = select_best_window(pleth, seconds)
    start_seconds = selection["起始秒"]
    segment = pleth[start_seconds * FS: (start_seconds + seconds) * FS]
    finite = segment[np.isfinite(segment)]
    missing_points = int(segment.size - finite.size)
    finite_ratio = float(finite.size / segment.size) if segment.size else 0.0
    detection_invalid = _invalid_sample_mask(segment)
    display_invalid = _display_invalid_sample_mask(segment)
    outlier_points = int(np.count_nonzero(display_invalid & np.isfinite(segment)))
    detection_outliers = int(
        np.count_nonzero(detection_invalid & np.isfinite(segment))
    )
    outlier_ratio = (
        float(outlier_points / segment.size) if segment.size else 0.0
    )
    cleaned = _clean_pleth_for_detection(segment)
    cleaned_finite = cleaned[np.isfinite(cleaned)]
    amplitude_range = (
        float(np.ptp(cleaned_finite)) if cleaned_finite.size else 0.0
    )

    issues = []
    if missing_fields:
        issues.append("病历字段缺失：" + "、".join(missing_fields))
    if missing_points:
        issues.append(f"波形缺失或非有限采样点 {missing_points} 个")
    if outlier_points:
        issues.append(
            f"检测到数据异常采样点 {outlier_points} 个"
            "（含幅度哨兵或起始基线未稳定），"
            f"显示图会断开异常段；其中 {detection_outliers} 个幅度哨兵"
            "在峰值检测时局部插值"
        )
    if finite_ratio < 0.9:
        issues.append(f"有效采样点比例仅 {finite_ratio:.1%}")
    if amplitude_range <= 0:
        issues.append("波形幅度没有变化")

    if (
        missing_fields
        or finite_ratio < 0.9
        or outlier_ratio > 0.1
        or amplitude_range <= 0
    ):
        quality = "不足"
    elif issues:
        quality = "警告"
    else:
        quality = "通过"

    return {
        "波形ID": selected_id,
        "原始数据时长秒": len(pleth) // FS,
        "检查时长秒": seconds,
        "选择窗口起始秒": start_seconds,
        "选择窗口结束秒": selection["结束秒"],
        "候选窗口数": selection["候选窗口数"],
        "选窗说明": selection["选择说明"],
        "病历字段完整": not missing_fields,
        "缺失病历字段": missing_fields,
        "采样点数": int(segment.size),
        "有效采样点比例": round(finite_ratio, 4),
        "异常采样点": outlier_points,
        "异常采样点比例": round(outlier_ratio, 4),
        "影响峰值检测的异常点": detection_outliers,
        "波形最小值": (
            round(float(np.min(cleaned_finite)), 3)
            if cleaned_finite.size else None
        ),
        "波形最大值": (
            round(float(np.max(cleaned_finite)), 3)
            if cleaned_finite.size else None
        ),
        "波形峰峰值": round(amplitude_range, 3),
        "波形质量": quality,
        "问题": issues,
        "是否可以继续分析": not missing_fields and quality != "不足",
    }
