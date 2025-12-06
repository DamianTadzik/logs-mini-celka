#!/usr/bin/env python3
"""
Parquet log cutter: extract time slices from large logs

Example:
    python parquet_cutter.py --input log.parquet --output cut.parquet \
                             --start 12.5 --end 34.2
"""
import argparse
import pandas as pd
from datetime import datetime

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input Parquet file path")
    parser.add_argument("--output", required=True, help="Output Parquet file path")
    parser.add_argument("--start", type=float, required=True, help="Start time (seconds since start)")
    parser.add_argument("--end", type=float, required=True, help="End time (seconds since start)")
    parser.add_argument("--time-col", default="seconds_since_start", help="Column name for time (default: seconds_since_start)")
    args = parser.parse_args()

    print(f"Loading {args.input}...")
    df = pd.read_parquet(args.input)
    print(f"Total rows: {len(df)}")

    # === Read and display input metadata ===
    try:
        meta = df.attrs
        if meta:
            print("[meta] Existing Parquet metadata:")
            for k, v in meta.items():
                print(f"    {k}: {v}")
        else:
            print("[meta] No metadata found in input file.")
    except Exception as e:
        print(f"[warn] Could not read metadata: {e}")
        meta = {}

    # === Verify time column existence ===
    if args.time_col not in df.columns:
        raise KeyError(f"Column '{args.time_col}' not found in {args.input}")

    # === Display time stats ===
    tmin, tmax = df[args.time_col].min(), df[args.time_col].max()
    print(f"[info] Time range available: {tmin:.6f} → {tmax:.6f} (span = {tmax - tmin:.3f} s)")

    # === Apply cut ===
    mask = (df[args.time_col] >= args.start) & (df[args.time_col] <= args.end)
    df_cut = df.loc[mask].copy()
    print(f"[info] Selected time window: {args.start:.3f} → {args.end:.3f}")
    print(f"[info] Rows selected: {len(df_cut)}")

    if len(df_cut) == 0:
        print("[warn] No rows match the specified time range!")

    # === Merge metadata ===
    new_meta = dict(meta)  # copy old
    new_meta.update({
        "cut_start_s": args.start,
        "cut_end_s": args.end,
        "cut_rows": str(len(df_cut)),
        "cut_generated_at": datetime.now().isoformat(timespec="seconds", sep=' '),
    })

    # === Attach and save ===
    df_cut.attrs.update(new_meta)
    df_cut.to_parquet(args.output, index=False)
    print(f"[ok] Saved {len(df_cut)} rows to {args.output}")

    # === Display final metadata ===
    print("\n[meta] Written metadata:")
    for k, v in new_meta.items():
        print(f"    {k}: {v}")
