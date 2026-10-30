"""工具 2：从患者绑定的 PLETH 波形计算心率。"""

import csv
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks

from patient import DEFAULT_WAVEFORM_ID, PATIENT_WAVEFORMS
from runtime_state import get_patient


CASES_DIR = Path(__file__).resolve().parent.parent / "data_cases"
FS = 500
RAW_WINDOW_SECONDS = 120
DEFAULT_SEGMENT_SECONDS = 60
MIN_SEGMENT_SECONDS = 5
MAX_SEGMENT_SECONDS = 60
WINDOW_CANDIDATE_STEP_SECONDS = 5
MIN_PEAK_DISTANCE_SECONDS = 0.4
PROMINENCE_THRESHOLD = 0.5
OUTLIER_IQR_MULTIPLIER = 5.0
INITIAL_STABILITY_SECONDS = 4.0

SCHEMA = {
    "type": "function",
    "function": {
        "name": "analyze_waveform",
        "description": (
            "从未截取的 120 秒 PPG 中自动选择质量最好且前后半段最稳定的"
            "分析窗口，并检测心跳，返回所选起止秒、算法心率、"
            "PLETH_HR（同源脉搏率）和综合 HR。默认分析 60 秒。"
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
                    "description": "分析的波形时长（秒），范围 5~60，默认 60",
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


def _resolve_waveform_id(waveform_id=None):
    patient = get_patient()
    return waveform_id or PATIENT_WAVEFORMS.get(
        patient.get("姓名"),
        DEFAULT_WAVEFORM_ID,
    )


def _load_pleth(path):
    values = []
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            raw = row.get("PLETH(a.u.)", "")
            try:
                values.append(float(raw))
            except (TypeError, ValueError):
                values.append(float("nan"))
    return np.asarray(values, dtype=float)


def _load_case_data(selected_id):
    case_dir = CASES_DIR / selected_id
    case_wave = case_dir / "waveform_120s.csv"
    case_num = case_dir / "numeric_120s.csv"
    if not case_wave.exists() or not case_num.exists():
        raise FileNotFoundError(f"找不到病例数据：{selected_id}")

    pleth = _load_pleth(case_wave)
    with open(case_num, encoding="utf-8-sig") as f:
        numeric_rows = list(csv.DictReader(f))
    return pleth, numeric_rows


def _clamp_segment_seconds(requested, sample_count):
    available = sample_count // FS
    return max(MIN_SEGMENT_SECONDS, min(int(requested), available, MAX_SEGMENT_SECONDS))


def _initial_baseline_mask(pleth):
    """标记起始基线尚未稳定、随后发生大台阶的初始片段。"""
    values = np.asarray(pleth, dtype=float)
    invalid = np.zeros(values.size, dtype=bool)
    minimum_samples = int(INITIAL_STABILITY_SECONDS * FS)
    if values.size < minimum_samples or not np.isfinite(values).any():
        return invalid

    finite = values[np.isfinite(values)]
    q25, q75 = np.quantile(finite, [0.25, 0.75])
    threshold = max(0.75 * float(q75 - q25), 10.0)
    initial_median = float(np.nanmedian(values[: FS // 2]))
    settled_median = float(np.nanmedian(values[2 * FS: 4 * FS]))
    if abs(initial_median - settled_median) <= threshold:
        return invalid

    scan_window = FS // 4
    scan_stop = min(values.size - scan_window, int(INITIAL_STABILITY_SECONDS * FS))
    transition = None
    for start in range(FS // 2, scan_stop, FS // 10):
        local_median = float(np.nanmedian(values[start:start + scan_window]))
        if abs(local_median - settled_median) <= threshold:
            transition = start
            break

    if transition is None:
        transition = FS // 2
    invalid[:transition] = True
    return invalid


def _invalid_sample_mask(pleth):
    """标记非有限值和远离主体分布的采样点。

    使用 1%/99% 分位数加 5 倍四分位距作为宽松边界，避免把正常脉搏波
    的陡峭上升沿或低基线误判为异常，同时能识别监护仪哨兵值。
    """
    values = np.asarray(pleth, dtype=float)
    invalid = ~np.isfinite(values)
    finite = values[~invalid]
    if finite.size < 4:
        return invalid

    q01, q25, q75, q99 = np.quantile(finite, [0.01, 0.25, 0.75, 0.99])
    iqr = float(q75 - q25)
    if iqr <= 0:
        return invalid

    lower = q01 - OUTLIER_IQR_MULTIPLIER * iqr
    upper = q99 + OUTLIER_IQR_MULTIPLIER * iqr
    return invalid | (values < lower) | (values > upper)


def _display_invalid_sample_mask(pleth):
    """图表不只断开哨兵，也断开起始基线尚未稳定的片段。"""
    values = np.asarray(pleth, dtype=float)
    return _invalid_sample_mask(values) | _initial_baseline_mask(values)


def _clean_pleth_for_detection(pleth):
    """把异常点局部插值后再交给峰值检测，保留原始数组长度。"""
    values = np.asarray(pleth, dtype=float)
    invalid = _invalid_sample_mask(values)
    if not invalid.any():
        return values.copy()

    cleaned = values.copy()
    valid_indices = np.flatnonzero(~invalid)
    if valid_indices.size == 0:
        return np.full_like(cleaned, np.nan)

    invalid_indices = np.flatnonzero(invalid)
    cleaned[invalid_indices] = np.interp(
        invalid_indices,
        valid_indices,
        values[valid_indices],
    )
    return cleaned


def _count_invalid_runs(mask):
    """统计连续异常点形成的时间区间数量。"""
    array = np.asarray(mask, dtype=bool)
    if not array.any():
        return 0
    return int(np.count_nonzero(array & ~np.r_[False, array[:-1]]))


def _analyze_segment(
    pleth,
    seconds,
    start_seconds=0,
    prominence=PROMINENCE_THRESHOLD,
    min_distance_seconds=MIN_PEAK_DISTANCE_SECONDS,
):
    start_sample = int(round(float(start_seconds) * FS))
    end_sample = start_sample + FS * int(seconds)
    raw_signal = np.asarray(pleth, dtype=float)[start_sample:end_sample]
    signal = _clean_pleth_for_detection(raw_signal)
    if not np.isfinite(signal).any():
        return np.asarray([], dtype=int), 0.0
    peaks, _ = find_peaks(
        signal,
        distance=FS * min_distance_seconds,
        prominence=prominence,
    )
    hr_est = len(peaks) * 60 / seconds
    return peaks, hr_est


def _reference_values(numeric_rows, seconds, start_seconds=0):
    start_seconds = float(start_seconds)
    end_seconds = start_seconds + int(seconds)
    window_rows = [
        row for row in numeric_rows
        if (
            row.get("时间(秒)")
            and start_seconds <= float(row["时间(秒)"]) < end_seconds
        )
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
    return ref_pleth, ref_hr


def evaluate_window_candidates(
    pleth,
    numeric_rows=None,
    window_seconds=DEFAULT_SEGMENT_SECONDS,
    step_seconds=WINDOW_CANDIDATE_STEP_SECONDS,
    prominence=PROMINENCE_THRESHOLD,
    min_distance_seconds=MIN_PEAK_DISTANCE_SECONDS,
):
    """评估 120 秒原始波形中的全部候选窗口。

    排序只使用缺失率、异常点比例和窗口前后半段心率差。即使传入
    numeric_rows，参考心率也只会在排序完成后附加到结果中。
    """
    values = np.asarray(pleth, dtype=float)
    available_seconds = len(values) // FS
    window_seconds = max(
        MIN_SEGMENT_SECONDS,
        min(int(window_seconds), available_seconds, MAX_SEGMENT_SECONDS),
    )
    step_seconds = max(1, int(step_seconds))
    latest_start = available_seconds - window_seconds
    starts = list(range(0, latest_start + 1, step_seconds))
    if starts[-1] != latest_start:
        starts.append(latest_start)

    first_seconds = window_seconds // 2
    second_seconds = window_seconds - first_seconds
    candidates = []
    for start_seconds in starts:
        start_sample = start_seconds * FS
        segment = values[start_sample:start_sample + window_seconds * FS]
        finite = np.isfinite(segment)
        missing_points = int(segment.size - finite.sum())
        finite_ratio = float(finite.mean()) if segment.size else 0.0

        display_invalid = _display_invalid_sample_mask(segment)
        detection_invalid = _invalid_sample_mask(segment)
        display_outliers = int(
            np.count_nonzero(display_invalid & np.isfinite(segment))
        )
        detection_outliers = int(
            np.count_nonzero(detection_invalid & np.isfinite(segment))
        )
        cleaned = _clean_pleth_for_detection(segment)
        clean_finite = cleaned[np.isfinite(cleaned)]
        amplitude_range = (
            float(np.ptp(clean_finite)) if clean_finite.size else 0.0
        )

        first_peaks, _ = _analyze_segment(
            segment,
            first_seconds,
            prominence=prominence,
            min_distance_seconds=min_distance_seconds,
        )
        second_peaks, _ = _analyze_segment(
            segment,
            second_seconds,
            start_seconds=first_seconds,
            prominence=prominence,
            min_distance_seconds=min_distance_seconds,
        )
        first_hr = len(first_peaks) * 60 / first_seconds
        second_hr = len(second_peaks) * 60 / second_seconds
        split_difference = abs(first_hr - second_hr)
        all_peaks, algorithm_hr = _analyze_segment(
            segment,
            window_seconds,
            prominence=prominence,
            min_distance_seconds=min_distance_seconds,
        )

        quality_penalty = int(finite_ratio < 0.9 or amplitude_range <= 0)
        candidates.append({
            "起始秒": start_seconds,
            "结束秒": start_seconds + window_seconds,
            "有效采样点比例": finite_ratio,
            "缺失采样点": missing_points,
            "异常采样点": display_outliers,
            "幅度哨兵点": detection_outliers,
            "异常采样点比例": (
                display_outliers / segment.size if segment.size else 1.0
            ),
            "波形峰峰值": amplitude_range,
            "检测心跳次数": int(len(all_peaks)),
            "算法心率": algorithm_hr,
            "前半段心率": first_hr,
            "后半段心率": second_hr,
            "前后半段心率差": split_difference,
            "_排序键": (
                quality_penalty,
                display_outliers,
                missing_points,
                split_difference,
                start_seconds,
            ),
        })

    ranked = sorted(candidates, key=lambda item: item["_排序键"])
    for rank, candidate in enumerate(ranked, 1):
        candidate["质量排名"] = rank
        candidate["是否选中"] = rank == 1
        if numeric_rows is not None:
            ref_pleth, ref_hr = _reference_values(
                numeric_rows,
                window_seconds,
                start_seconds=candidate["起始秒"],
            )
            candidate["PLETH_HR"] = ref_pleth
            candidate["HR"] = ref_hr
            candidate["同源差"] = abs(candidate["算法心率"] - ref_pleth)
            candidate["综合HR差"] = abs(candidate["算法心率"] - ref_hr)

    public_candidates = []
    for candidate in ranked:
        cleaned_candidate = {
            key: value
            for key, value in candidate.items()
            if not key.startswith("_")
        }
        for key in (
            "算法心率",
            "前半段心率",
            "后半段心率",
            "前后半段心率差",
            "PLETH_HR",
            "HR",
            "同源差",
            "综合HR差",
        ):
            if key in cleaned_candidate:
                cleaned_candidate[key] = round(
                    float(cleaned_candidate[key]),
                    1,
                )
        public_candidates.append(cleaned_candidate)

    return {
        "窗口秒": window_seconds,
        "候选窗口数": len(public_candidates),
        "选窗步长秒": step_seconds,
        "候选窗口": public_candidates,
    }


def select_best_window(
    pleth,
    window_seconds=DEFAULT_SEGMENT_SECONDS,
    step_seconds=WINDOW_CANDIDATE_STEP_SECONDS,
    prominence=PROMINENCE_THRESHOLD,
    min_distance_seconds=MIN_PEAK_DISTANCE_SECONDS,
):
    """从候选窗口中选择质量最好且最稳定的分析窗口。"""
    evaluation = evaluate_window_candidates(
        pleth,
        window_seconds=window_seconds,
        step_seconds=step_seconds,
        prominence=prominence,
        min_distance_seconds=min_distance_seconds,
    )
    candidates = evaluation["候选窗口"]
    best = candidates[0]
    explanation_parts = []
    if best["异常采样点"] == 0:
        explanation_parts.append("无异常采样点")
    else:
        explanation_parts.append(f"异常采样点 {best['异常采样点']} 个")
    if best["缺失采样点"] == 0:
        explanation_parts.append("无缺失采样点")
    else:
        explanation_parts.append(f"缺失采样点 {best['缺失采样点']} 个")
    explanation_parts.append(
        f"前后半段心率差 {best['前后半段心率差']:.1f} 次/分"
    )

    return {
        "窗口秒": window_seconds,
        "起始秒": best["起始秒"],
        "结束秒": best["结束秒"],
        "候选窗口数": evaluation["候选窗口数"],
        "选窗步长秒": step_seconds,
        "选择方式": "质量优先，其次前后半段心率稳定性；未使用参考心率",
        "选择说明": "；".join(explanation_parts),
        "候选摘要": candidates[:3],
    }


def compare_selection_policies(candidates):
    """对比固定首窗、质量选窗、当前策略和参考最优上界。"""
    if not candidates:
        raise ValueError("候选窗口为空，无法比较选窗策略")

    def quality_key(item):
        quality_penalty = int(
            item["有效采样点比例"] < 0.9
            or item["波形峰峰值"] <= 0
        )
        return (
            quality_penalty,
            item["异常采样点"],
            item["缺失采样点"],
            item["起始秒"],
        )

    fixed = min(candidates, key=lambda item: abs(item["起始秒"]))
    quality_only = min(candidates, key=quality_key)
    current = next(item for item in candidates if item["是否选中"])
    if "同源差" not in candidates[0]:
        raise ValueError("策略对比需要带参考心率的候选窗口")
    oracle = min(
        candidates,
        key=lambda item: (
            item["同源差"],
            item["综合HR差"],
            item["起始秒"],
        ),
    )

    definitions = [
        ("固定首窗", fixed, "始终使用 0–60 秒，不使用质量和参考信息"),
        ("仅信号质量", quality_only, "只按异常点、缺失点和幅度选窗"),
        ("质量+稳定性", current, "当前部署策略，不读取参考心率"),
        (
            "参考最优",
            oracle,
            "按参考心率误差选择，仅作评估上界，不能用于生产",
        ),
    ]
    return [
        {
            "策略": label,
            "窗口起始秒": candidate["起始秒"],
            "窗口结束秒": candidate["结束秒"],
            "算法心率": candidate["算法心率"],
            "PLETH_HR": candidate["PLETH_HR"],
            "HR": candidate["HR"],
            "同源差": candidate["同源差"],
            "综合HR差": candidate["综合HR差"],
            "使用参考心率选窗": label == "参考最优",
            "说明": explanation,
        }
        for label, candidate, explanation in definitions
    ]


def analyze_waveform(segment_seconds=DEFAULT_SEGMENT_SECONDS, waveform_id=None):
    selected_id = _resolve_waveform_id(waveform_id)
    pleth, numeric_rows = _load_case_data(selected_id)
    seconds = _clamp_segment_seconds(segment_seconds, len(pleth))
    selection = select_best_window(pleth, seconds)
    start_seconds = selection["起始秒"]
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

    return {
        "波形ID": selected_id,
        "原始数据时长秒": len(pleth) // FS,
        "分析窗口起始秒": start_seconds,
        "分析窗口结束秒": selection["结束秒"],
        "候选窗口数": selection["候选窗口数"],
        "窗口选择说明": selection["选择说明"],
        "分析时长秒": seconds,
        "参考窗口秒": seconds,
        "检测心跳次数": int(len(peaks)),
        "算法心率": round(hr_est, 1),
        "PLETH_HR": round(ref_pleth, 1),
        "HR": round(ref_hr, 1),
        "监护仪对照心率": round(ref_pleth, 1),
    }
