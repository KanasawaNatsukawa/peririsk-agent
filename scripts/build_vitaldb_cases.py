"""Download five VitalDB cases and extract time-aligned 60-second samples.

The script chooses the first window satisfying a fixed quality rule:
>=90% valid PLETH and >=10 valid readings in both HR tracks. It does not
choose windows by minimizing the error.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from vitaldb.utils import VitalFile


ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data_cases"
LOCAL_CASE_1 = Path(r"E:\数字孪生\python\1.parquet")
CASE_IDS = [1, 2, 3, 4, 5]
WINDOW_SECONDS = 60
FS = 500
URL_TEMPLATE = "https://api.vitaldb.net/1.0.1/{case_id}.vital"


def load_case_file(case_id: int) -> VitalFile:
    if case_id == 1 and LOCAL_CASE_1.exists():
        return VitalFile(str(LOCAL_CASE_1))
    return VitalFile(URL_TEMPLATE.format(case_id=case_id))


def first_aligned_window(pl_ts, pleth, hr_ts, hr_tracks):
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


def process_case(case_id: int):
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

    start = first_aligned_window(pl_ts, pleth, hr_ts, hr_tracks)
    end = start + WINDOW_SECONDS
    wave_mask = (pl_ts >= start) & (pl_ts < end)
    hr_mask = (hr_ts >= start) & (hr_ts < end)

    pleth_window = fill_gaps(pleth[wave_mask])
    peaks, _ = find_peaks(
        pleth_window,
        distance=FS * 0.4,
        prominence=0.5,
    )
    algorithm_hr = len(peaks) * 60 / WINDOW_SECONDS

    hr_values = hr[hr_mask]
    pleth_hr_values = pleth_hr[hr_mask]
    hr_mean = float(np.nanmean(hr_values))
    pleth_hr_mean = float(np.nanmean(pleth_hr_values))

    case_dir = OUT_DIR / f"case_{case_id:03d}"
    case_dir.mkdir(parents=True, exist_ok=True)
    wave_df = pd.DataFrame({
        "时间(秒)": np.round(pl_ts[wave_mask] - start, 3),
        "PLETH(a.u.)": np.round(pleth_window, 4),
    })
    wave_df.to_csv(
        case_dir / "waveform_60s.csv",
        index=False,
        encoding="utf-8-sig",
    )
    num_df = pd.DataFrame({
        "时间(秒)": np.round(hr_ts[hr_mask] - start, 3),
        "Solar8000_HR(次/分)": hr_values,
        "Solar8000_PLETH_HR(次/分)": pleth_hr_values,
    })
    num_df.to_csv(
        case_dir / "numeric_60s.csv",
        index=False,
        encoding="utf-8-sig",
    )

    return {
        "waveform_id": f"case_{case_id:03d}",
        "case_id": case_id,
        "source": str(LOCAL_CASE_1) if case_id == 1 else URL_TEMPLATE.format(case_id=case_id),
        "window_start_epoch": round(start, 3),
        "window_seconds": WINDOW_SECONDS,
        "pleth_points": len(pleth_window),
        "valid_hr_readings": int(np.isfinite(hr_values).sum()),
        "valid_pleth_hr_readings": int(np.isfinite(pleth_hr_values).sum()),
        "algorithm_hr": round(float(algorithm_hr), 1),
        "solar_hr": round(hr_mean, 1),
        "pleth_hr": round(pleth_hr_mean, 1),
        "same_source_diff": round(abs(float(algorithm_hr) - pleth_hr_mean), 1),
        "cross_source_diff": round(abs(float(algorithm_hr) - hr_mean), 1),
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = [process_case(case_id) for case_id in CASE_IDS]
    with open(OUT_DIR / "manifest.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(row)
    print(f"wrote {OUT_DIR / 'manifest.csv'}")


if __name__ == "__main__":
    main()
