"""Download VitalDB cases and extract time-aligned 120-second samples.

The 60-second analysis window is selected later by the local tools using
signal quality and stability only. The extraction step keeps a source
anchor and never selects a window by minimizing heart-rate error.
"""

from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from vitaldb.utils import VitalFile


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.waveform import _load_case_data, evaluate_window_candidates

OUT_DIR = ROOT / "data_cases"
LOCAL_CASE_1 = Path(r"E:\数字孪生\python\1.parquet")
TARGET_CASE_COUNT = 20
FIRST_NEW_CASE_ID = 6
MAX_CASE_ID = 200
MAX_SELECTED_SAME_SOURCE_DIFF = 5.0
MAX_SELECTED_CROSS_SOURCE_DIFF = 8.0
MIN_SELECTED_HEART_RATE = 30.0
MAX_SELECTED_HEART_RATE = 180.0
WINDOW_SECONDS = 120
FS = 500
URL_TEMPLATE = "https://api.vitaldb.net/1.0.1/{case_id}.vital"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_case_file(case_id: int) -> VitalFile:
    if case_id == 1 and LOCAL_CASE_1.exists():
        return VitalFile(str(LOCAL_CASE_1))
    return VitalFile(URL_TEMPLATE.format(case_id=case_id))


def existing_source_starts():
    """保留旧 manifest 的来源起点，确保 120 秒只是向后延长。"""
    manifest = OUT_DIR / "manifest.csv"
    if not manifest.exists():
        return {}

    starts = {}
    with open(manifest, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            start = row.get("source_window_start_epoch") or row.get("window_start_epoch")
            if start:
                starts[int(row["case_id"])] = float(start)
    return starts


def first_aligned_window(pl_ts, pleth, hr_tracks):
    pl_valid = np.isfinite(pleth)
    overlap_start = max(
        np.nanmin(pl_ts[pl_valid]),
        min(np.nanmin(ts[np.isfinite(values)]) for ts, values in hr_tracks.values()),
    )
    overlap_end = min(
        np.nanmax(pl_ts[pl_valid]),
        max(np.nanmax(ts[np.isfinite(values)]) for ts, values in hr_tracks.values()),
    )

    for start in np.arange(overlap_start, overlap_end - WINDOW_SECONDS, 1.0):
        wave_mask = (pl_ts >= start) & (pl_ts < start + WINDOW_SECONDS)
        if wave_mask.sum() == 0:
            continue
        if np.isfinite(pleth[wave_mask]).mean() < 0.90:
            continue
        if all(
            (
                (ts >= start)
                & (ts < start + WINDOW_SECONDS)
                & np.isfinite(values)
            ).sum()
            >= 10
            for ts, values in hr_tracks.values()
        ):
            return float(start)
    raise RuntimeError("No aligned 60-second window satisfies the quality rule")


def fill_gaps(values):
    values = np.asarray(values, dtype=float)
    valid = np.isfinite(values)
    if valid.all():
        return values
    indices = np.arange(len(values))
    return np.interp(indices, indices[valid], values[valid])


def process_case(case_id: int, source_start=None):
    vf = load_case_file(case_id)
    data, _ = vf.get_samples(["SNUADC/PLETH"], None, return_timestamp=True)
    pl_ts, pleth = map(np.asarray, data)
    data, _ = vf.get_samples(
        ["Solar8000/HR", "Solar8000/PLETH_HR"],
        1,
        return_timestamp=True,
    )
    hr_ts, hr, pleth_hr = map(np.asarray, data)
    hr_tracks = {
        "Solar8000/HR": (hr_ts, hr),
        "Solar8000/PLETH_HR": (hr_ts, pleth_hr),
    }

    start = (
        float(source_start)
        if source_start is not None
        else first_aligned_window(pl_ts, pleth, hr_tracks)
    )
    end = start + WINDOW_SECONDS
    wave_mask = (pl_ts >= start) & (pl_ts < end)
    hr_mask = (hr_ts >= start) & (hr_ts < end)

    pleth_window = fill_gaps(pleth[wave_mask])
    hr_values = hr[hr_mask]
    pleth_hr_values = pleth_hr[hr_mask]
    if len(pleth_window) != WINDOW_SECONDS * FS:
        raise RuntimeError(
            f"病例 {case_id} 提取点数异常：{len(pleth_window)}"
        )
    if (
        int(np.isfinite(hr_values).sum()) < 10
        or int(np.isfinite(pleth_hr_values).sum()) < 10
    ):
        raise RuntimeError(f"病例 {case_id} 的心率参考读数不足")

    case_dir = OUT_DIR / f"case_{case_id:03d}"
    case_dir.mkdir(parents=True, exist_ok=True)
    wave_df = pd.DataFrame({
        "时间(秒)": np.round(pl_ts[wave_mask] - start, 3),
        "PLETH(a.u.)": np.round(pleth_window, 4),
    })
    wave_df.to_csv(
        case_dir / "waveform_120s.csv",
        index=False,
        encoding="utf-8-sig",
    )
    num_df = pd.DataFrame({
        "时间(秒)": np.round(hr_ts[hr_mask] - start, 3),
        "Solar8000_HR(次/分)": hr_values,
        "Solar8000_PLETH_HR(次/分)": pleth_hr_values,
    })
    num_df.to_csv(
        case_dir / "numeric_120s.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return {
        "waveform_id": f"case_{case_id:03d}",
        "case_id": case_id,
        "source": str(LOCAL_CASE_1) if case_id == 1 else URL_TEMPLATE.format(case_id=case_id),
        "source_window_start_epoch": round(start, 3),
        "source_window_seconds": WINDOW_SECONDS,
        "pleth_points": len(pleth_window),
        "valid_hr_readings": int(np.isfinite(hr_values).sum()),
        "valid_pleth_hr_readings": int(np.isfinite(pleth_hr_values).sum()),
    }


def _read_manifest():
    manifest = OUT_DIR / "manifest.csv"
    if not manifest.exists():
        return []
    with open(manifest, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _quality_check(case_id):
    """拒绝严重失真的病例，但不参与运行时 60 秒窗口选择。"""
    waveform_id = f"case_{case_id:03d}"
    pleth, numeric_rows = _load_case_data(waveform_id)
    evaluation = evaluate_window_candidates(
        pleth,
        numeric_rows=numeric_rows,
    )
    selected = evaluation["候选窗口"][0]
    checks = {
        "selected_window_start": selected["起始秒"],
        "algorithm_hr": selected["算法心率"],
        "pleth_hr": selected["PLETH_HR"],
        "same_source_diff": selected["同源差"],
        "cross_source_diff": selected["综合HR差"],
    }
    if not MIN_SELECTED_HEART_RATE <= selected["算法心率"] <= MAX_SELECTED_HEART_RATE:
        raise RuntimeError(
            f"算法心率 {selected['算法心率']} 超出演示范围"
        )
    if selected["同源差"] > MAX_SELECTED_SAME_SOURCE_DIFF:
        raise RuntimeError(
            f"同源差 {selected['同源差']} 超过质量门槛"
        )
    if selected["综合HR差"] > MAX_SELECTED_CROSS_SOURCE_DIFF:
        raise RuntimeError(
            f"综合 HR 差 {selected['综合HR差']} 超过质量门槛"
        )
    return checks


def _write_manifest(rows):
    with open(OUT_DIR / "manifest.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source_starts = existing_source_starts()
    existing_rows = sorted(_read_manifest(), key=lambda row: int(row["case_id"]))
    rows = []
    seen_ids = {int(row["case_id"]) for row in existing_rows}
    for row in existing_rows:
        case_id = int(row["case_id"])
        try:
            quality = _quality_check(case_id)
        except Exception as exc:
            print(f"[剔除 {case_id}] {exc}", flush=True)
            case_dir = OUT_DIR / f"case_{case_id:03d}"
            if case_dir.exists():
                shutil.rmtree(case_dir)
            continue
        rows.append({**row, **quality})

    case_id = max(FIRST_NEW_CASE_ID, max(seen_ids, default=0) + 1)
    while len(rows) < TARGET_CASE_COUNT and case_id <= MAX_CASE_ID:
        if case_id in seen_ids:
            case_id += 1
            continue
        print(
            f"[尝试 {case_id}] 当前成功 {len(rows)}/{TARGET_CASE_COUNT}",
            flush=True,
        )
        try:
            row = process_case(case_id, source_starts.get(case_id))
        except Exception as exc:
            print(f"  跳过 {case_id}：{exc}", flush=True)
            case_id += 1
            continue
        try:
            quality = _quality_check(case_id)
        except Exception as exc:
            print(f"  质量控制跳过 {case_id}：{exc}", flush=True)
            case_dir = OUT_DIR / f"case_{case_id:03d}"
            if case_dir.exists():
                shutil.rmtree(case_dir)
            seen_ids.add(case_id)
            case_id += 1
            continue
        rows.append({**row, **quality})
        seen_ids.add(case_id)
        _write_manifest(rows)
        print(f"  完成 {row['waveform_id']}：{row}", flush=True)
        case_id += 1

    if len(rows) < TARGET_CASE_COUNT:
        raise RuntimeError(
            f"只成功导出 {len(rows)} 个病例，目标为 {TARGET_CASE_COUNT}"
        )
    _write_manifest(rows)
    print(f"已完成 {len(rows)} 个病例", flush=True)
    print(f"wrote {OUT_DIR / 'manifest.csv'}")


if __name__ == "__main__":
    main()
