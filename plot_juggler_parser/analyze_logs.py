#!/usr/bin/env python3
"""
Analyze CAN log TXT files — compute frequency, jitter, bus load, and timing statistics per CAN ID.

Usage:
  python analyze_logs.py \
    --input LOG012.TXT \
    --dbc path/to/file.dbc \
    [--csv result.csv] \
    [--can-baud-rate 500000] \
    [--verbose]
"""

import os
import argparse
import datetime
import re
import numpy as np
import pandas as pd
import cantools

timestamp_pattern = re.compile(r"^\d{2}:\d{2}:\d{2},\d{3}$")

def is_valid_hex(s: str) -> bool:
    return all(c in "0123456789ABCDEFabcdef" for c in s)


# =======================================================
def parse_log(input_path, verbose=False):
    """Parse log file and return dict of {id_int: [timestamps]}"""
    can_frames = {}
    line_count = 0
    corrupted = 0
    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            line_count += 1
            spl = line.split(";")
            if len(spl) != 3:
                corrupted += 1
                continue
            timestamp_str, id_str, _ = spl
            if not timestamp_pattern.match(timestamp_str):
                corrupted += 1
                continue
            if not (len(id_str) == 2 and is_valid_hex(id_str)):
                corrupted += 1
                continue
            try:
                timestamp = datetime.datetime.strptime(timestamp_str, "%H:%M:%S,%f")
                can_id = int(id_str, 16)
            except Exception:
                corrupted += 1
                continue
            can_frames.setdefault(can_id, []).append(timestamp)
    print(f"[parse] {line_count} lines read, {corrupted} corrupted ({corrupted/line_count*100:.2f}%)")
    return can_frames


# =======================================================
def analyze_frames(can_frames, dbc_path=None):
    """Compute frequency, jitter, and period statistics for each CAN ID"""
    results = []
    dbc = None
    if dbc_path and os.path.exists(dbc_path):
        dbc = cantools.database.load_file(dbc_path)

    for can_id, ts_list in can_frames.items():
        ts_list = sorted(ts_list)
        msg_name = "(unmapped)"
        if dbc:
            try:
                msg_name = dbc.get_message_by_frame_id(can_id).name
            except Exception:
                pass

        if len(ts_list) < 2:
            mean_p = std_p = freq = jitter = np.nan
            collisions = 0
        else:
            ts_ns = np.array(ts_list, dtype="datetime64[ms]")
            deltas = np.diff(ts_ns).astype(float)
            # Detect same-timestamp collisions (0 ms delta)
            collisions = int(np.sum(deltas == 0.0))
            mean_p = np.mean(deltas[deltas > 0]) if np.any(deltas > 0) else np.nan
            std_p = np.std(deltas[deltas > 0]) if np.any(deltas > 0) else np.nan
            jitter = (std_p / mean_p) * 100 if mean_p > 0 else np.nan
            freq = 1000.0 / mean_p if mean_p > 0 else np.nan

        results.append({
            "ID_hex": f"0x{can_id:02X}",
            "Message": msg_name,
            "Count": len(ts_list),
            "Mean_period_ms": round(mean_p, 3) if not np.isnan(mean_p) else None,
            "Std_ms": round(std_p, 3) if not np.isnan(std_p) else None,
            "Jitter_%": round(jitter, 2) if not np.isnan(jitter) else None,
            "Freq_Hz": round(freq, 3) if not np.isnan(freq) else None,
            "Timestamp_collisions": collisions,
        })
    return pd.DataFrame(results)


# =======================================================
def compute_bus_load(df, can_baud_rate, duration_s):
    """Estimate CAN bus load (%) assuming 8B frames and 47-bit overhead"""
    if df.empty or duration_s <= 0:
        return 0.0

    bits_per_frame = 47 + (8 * 8) + 3  # overhead + payload + interframe space = ~114 bits
    total_frames = df["Count"].sum()
    total_bits = total_frames * bits_per_frame
    load = (total_bits / (can_baud_rate * duration_s)) * 100.0
    return load


# =======================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze CAN log file frequencies and periods.")
    parser.add_argument("--input", required=True, help="Path to TXT log file")
    parser.add_argument("--dbc", help="Optional DBC file for message names")
    parser.add_argument("--csv", help="Optional CSV output path")
    parser.add_argument("--can-baud-rate", type=int, default=125000,
                        help="CAN baud rate in bits per second (default: 125000)")
    parser.add_argument("--verbose", action="store_true", help="Print detailed info")
    args = parser.parse_args()

    can_frames = parse_log(args.input, verbose=args.verbose)
    df = analyze_frames(can_frames, args.dbc)
    df.sort_values("Freq_Hz", ascending=False, inplace=True, ignore_index=True)

    # Compute total log duration
    all_ts = [t for sub in can_frames.values() for t in sub]
    total_duration = (max(all_ts) - min(all_ts)).total_seconds() if all_ts else 0
    total_frames = sum(len(v) for v in can_frames.values())

    # Compute bus load
    bus_load = compute_bus_load(df, args.can_baud_rate, total_duration)

    # Print summary table
    print("\n=== CAN Message Frequency Summary ===")
    print(df.to_string(index=False))

    # Print global stats
    print("\n=== Log Statistics ===")
    print(f"[stats] Total log duration: {datetime.timedelta(seconds=total_duration)} ({total_duration:.1f} s)")
    print(f"[stats] Unique CAN IDs: {len(can_frames)}")
    print(f"[stats] Frames parsed: {total_frames}")
    print(f"[stats] Estimated bus load @ {args.can_baud_rate/1000:.0f} kbps: {bus_load:.2f} %")

    # Save CSV if requested
    if args.csv:
        df.to_csv(args.csv, index=False)
        print(f"[ok] Saved CSV summary to {args.csv}")
