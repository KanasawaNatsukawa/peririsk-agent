"""工具 2：从患者绑定的 PLETH 波形计算心率。"""

import csv
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks

from patient import DEFAULT_WAVEFORM_ID, PATIENT_WAVEFORMS
from runtime_state import get_patient


CASES_DIR = Path(__file__).resolve().parent.parent / "data_cases"

SCHEMA = {
    "type": "function",
    "function": {
        "name": "analyze_waveform",
        "description": (
            "分析患者绑定的监护仪脉搏波并检测心跳，返回算法心率、"
            "PLETH_HR（同源脉搏率）和综合 HR。建议先取 60 秒。"
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
                    "description": "分析的波形时长（秒），范围 5~120，默认 60",
                },
            },
        },
    },
}


def _finite_mean(values):
    clean = []
    for value in values:
        if value in (None, ""):
            continue
        try:
            clean.append(float(value))
        except (TypeError, ValueError):
            continue
    arr = np.asarray(clean, dtype=float)
    arr = arr[np.isfinite(arr)]
    return float(arr.mean()) if arr.size else float("nan")


def analyze_waveform(segment_seconds=60, waveform_id=None):
    patient = get_patient()
    selected_id = waveform_id or PATIENT_WAVEFORMS.get(
        patient.get("姓名"),
        DEFAULT_WAVEFORM_ID,
    )
    case_wave = CASES_DIR / selected_id / "waveform_60s.csv"
    case_num = CASES_DIR / selected_id / "numeric_60s.csv"
    if not case_wave.exists() or not case_num.exists():
        raise FileNotFoundError(f"找不到病例数据：{selected_id}")

    pleth = []
    with open(case_wave, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            pleth.append(float(row["PLETH(a.u.)"]))
    pleth = np.array(pleth)
    fs = 500
    seconds = max(5, min(segment_seconds, len(pleth) // fs))
    peaks, _ = find_peaks(
        pleth[: fs * seconds],
        distance=fs * 0.4,
        prominence=0.5,
    )
    hr_est = len(peaks) * 60 / seconds

    with open(case_num, encoding="utf-8-sig") as f:
        numeric_rows = list(csv.DictReader(f))
    window_rows = [
        row for row in numeric_rows
        if row.get("时间(秒)") and float(row["时间(秒)"]) < seconds
    ]
    ref_pleth = _finite_mean([
        row["Solar8000_PLETH_HR(次/分)"] for row in window_rows
    ])
    ref_hr = _finite_mean([
        row["Solar8000_HR(次/分)"] for row in window_rows
    ])
    if not np.isfinite(ref_pleth):
        ref_pleth = ref_hr
    if not np.isfinite(ref_hr):
        ref_hr = ref_pleth

    return {
        "波形ID": selected_id,
        "分析时长秒": seconds,
        "参考窗口秒": seconds,
        "检测心跳次数": int(len(peaks)),
        "算法心率": round(hr_est, 1),
        "PLETH_HR": round(ref_pleth, 1),
        "HR": round(ref_hr, 1),
        "监护仪对照心率": round(ref_pleth, 1),
    }
