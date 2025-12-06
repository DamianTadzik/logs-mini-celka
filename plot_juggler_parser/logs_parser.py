#!/usr/bin/env python3
"""
TXT → Parquet log converter for Celka / PlotJuggler

Usage example:
python plot_juggler_parser/logs_parser.py \
--dbc D:/Dane/workspace/can-messages-mini-celka/can_messages_mini_celka.dbc \
--input F:/LOG014.TXT \
--output D:/Dane/workspace/can-logs-mini-celka/logs_parquet/LOG014.parquet \
--verbose

"""

import os
import re
import sys
import argparse
import datetime
import struct
from typing import Set
import cantools
import pandas as pd
import numpy as np


# ========== Helper functions ==========

def human_readable_size(size, decimal_places=2) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.{decimal_places}f} {unit}"
        size /= 1024


def is_valid_hex(s: str) -> bool:
    valid_chars = set("0123456789ABCDEFabcdef")
    return all(c in valid_chars for c in s)

timestamp_pattern = re.compile(r"^\d{2}:\d{2}:\d{2},\d{3}$")  # strict HH:MM:SS,mmm format

# ========== NKPL core ==========

class NKPL:
    """
    NKPL — Niezły Kurczę Parser Logów :)
    Decodes TXT logs to structured data.
    """

    def __init__(self):
        # Ignored IDs
        self.ignored_ids: Set[int] = set()
        self.init_and_clear_fields()

    # ------------------------------------
    def init_and_clear_fields(self) -> None:
        self.corrupted_line_counter = 0
        self.line_counter = 0
        self.id_exception_counter = 0
        self.ignored_messages_counter = 0
        self.decoded_messages_counter = 0
        self.database = dict()

    # ------------------------------------
    def set_ignored_ids(self, ids: Set[int] = set()) -> None:
        self.ignored_ids = set(ids)

    # ------------------------------------
    def parse_and_decode(self, dbc_path: str, log_path: str, PRINT_ADDITIONAL_INFO=False):
        """Decode TXT log file using DBC definition."""
        self.init_and_clear_fields()
        print(f"[decode] Using DBC: {dbc_path}")
        print(f"[decode] Input log: {log_path}")

        dbc = cantools.database.load_file(dbc_path)
        line_count = sum(1 for _ in open(log_path, 'r', encoding='utf-8', errors='ignore'))
        print(f"[decode] {line_count} lines detected ({human_readable_size(os.path.getsize(log_path))})")

        with open(log_path, 'r', encoding='utf-8', errors='ignore') as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith("#"):
                    # skip comments and empty lines
                    continue
                self.line_counter += 1

                # Parse expected structure HH:MM:SS,KKK;ID;DATA
                spl = line.split(';')
                if len(spl) != 3:
                    self.handle_corrupted_line(line, "Split != 3")
                    continue

                timestamp_str, id_str, payload_str = spl


                # Validate timestamp strictly
                if not timestamp_pattern.match(timestamp_str):
                    self.handle_corrupted_line(line, "Bad timestamp format")
                    continue

                # Validate timestamp
                try:
                    timestamp = datetime.datetime.strptime(timestamp_str, '%H:%M:%S,%f')

                    # Initialize tracking
                    if not hasattr(self, "_first_timestamp"):
                        self._first_timestamp = timestamp
                        self._last_timestamp = timestamp
                    else:
                        # If time goes backward → corrupted line, skip it
                        if timestamp < self._last_timestamp:
                            self.handle_corrupted_line(line, "Timestamp jump backwards")
                            continue
                        self._last_timestamp = timestamp

                except Exception:
                    self.handle_corrupted_line(line, "Bad timestamp")
                    continue

                # Validate ID
                if not (len(id_str) == 2 and is_valid_hex(id_str)):
                    self.handle_corrupted_line(line, "Bad ID format")
                    continue
                try:
                    can_id = int(id_str, 16)
                except Exception:
                    self.handle_corrupted_line(line, "Bad ID int")
                    continue

                # Validate payload
                if not (len(payload_str) == 16 and is_valid_hex(payload_str)):
                    self.handle_corrupted_line(line, "Bad payload length/format")
                    continue
                try:
                    payload = bytes.fromhex(payload_str)
                except Exception:
                    self.handle_corrupted_line(line, "Payload parse fail")
                    continue

                # Skip ignored IDs
                if can_id in self.ignored_ids:
                    self.ignored_messages_counter += 1
                    continue

                # Decode CAN frame
                try:
                    message = dbc.get_message_by_frame_id(can_id)
                    decoded = message.decode(payload)
                except Exception as e:
                    self.id_exception_counter += 1
                    if PRINT_ADDITIONAL_INFO:
                        print(f"[warn] ID 0x{can_id:X} decode fail: {e}")
                    continue

                # FLOAT32_IEEE conversion
                for signal in message.signals:
                    unit = signal.unit or ""
                    if "FLOAT32_IEEE" in unit and signal.name in decoded:
                        raw = decoded[signal.name]
                        if isinstance(raw, int):
                            try:
                                decoded[signal.name] = struct.unpack('<f', raw.to_bytes(4, 'little'))[0]
                            except Exception:
                                pass

                # Store decoded values
                for key, val in decoded.items():
                    # name = f"{message.name}__{key}"
                    name = f"{message.name}/{key}"
                    if name not in self.database:
                        self.database[name] = {'timestamps': [], 'values': []}
                    self.database[name]['timestamps'].append(timestamp)
                    self.database[name]['values'].append(val)

                # Count this as one decoded CAN frame
                self.decoded_messages_counter += 1


        # Compute timespan directly from first and last valid log timestamps
        self.min_dt = getattr(self, "_first_timestamp", None)
        self.max_dt = getattr(self, "_last_timestamp", None)


        print(f"[decode] Done. {self.line_counter} lines, "
              f"{self.corrupted_line_counter} corrupted, "
              f"{self.decoded_messages_counter} decoded.")

        if PRINT_ADDITIONAL_INFO:
            self.print_stats()

    # ------------------------------------
    def handle_corrupted_line(self, line: str, reason: str = None) -> None:
        self.corrupted_line_counter += 1
        if reason:
            print(f"[corrupt] {reason}: {line}")

    # ------------------------------------
    def print_stats(self):
        if not self.line_counter:
            return
        perc = (self.corrupted_line_counter / self.line_counter) * 100
        print(f"[stats] Corrupted lines: {self.corrupted_line_counter} ({perc:.2f}%)")
        print(f"[stats] ID exceptions: {self.id_exception_counter}")
        print(f"[stats] Ignored messages: {self.ignored_messages_counter}")
        print(f"[stats] Decoded messages: {self.decoded_messages_counter}")
        if self.min_dt and self.max_dt:
            span = self.max_dt - self.min_dt
            print(f"[stats] Timespan from: {self.min_dt.strftime('%H:%M:%S.%f')[:-3]} to: "
                  f"{self.max_dt.strftime('%H:%M:%S.%f')[:-3]} duration: {span}")

    # -----------------------------------
    def to_dataframe(self) -> pd.DataFrame:
        """Convert database to pandas DataFrame (wide format, time-aligned)."""
        if not self.database:
            print("[warn] No decoded data to export.")
            return pd.DataFrame()

        # Flatten all timestamp/signal/value triplets
        records = []
        for name, rec in self.database.items():
            for ts, val in zip(rec["timestamps"], rec["values"]):
                records.append((ts, name, val))

        df = pd.DataFrame(records, columns=["timestamp", "signal", "value"])
        df.sort_values("timestamp", inplace=True, ignore_index=True)

        # Detect duplicate (timestamp, signal) pairs
        dup_counts = df.groupby(["timestamp", "signal"]).size()
        dup_counts = dup_counts[dup_counts > 1]
        if not dup_counts.empty:
            print(f"[warn] {len(dup_counts)} duplicate signal-timestamp pairs found.")
            # print(dup_counts.head(10))
            print("[info] Keeping last occurrence for duplicates.")

        # Pivot to wide format, resolving duplicates with 'last'
        df_wide = df.pivot_table(
            index="timestamp",
            columns="signal",
            values="value",
            aggfunc="last"
        )

        # Convert timestamp → seconds since start
        t0 = df_wide.index[0]
        df_wide.insert(0, "seconds_since_start", (df_wide.index - t0).total_seconds().astype("float64"))

        df_wide.reset_index(drop=True, inplace=True)

        print(f"[dataframe] Created DataFrame with shape {df_wide.shape}")
        return df_wide

    # ------------------------------------
    def export_parquet(self, df: pd.DataFrame, output_path: str, dbc_path: str, input_path: str = None):
        if df.empty:
            print("[warn] Empty DataFrame — skipping save.")
            return

        # Gather file metadata if available
        if input_path and os.path.exists(input_path):
            ctime = datetime.datetime.fromtimestamp(os.path.getctime(input_path)).isoformat(sep=" ", timespec="seconds")
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(input_path)).isoformat(sep=" ", timespec="seconds")
        else:
            ctime = mtime = ""

        # Attach metadata to Parquet file
        meta = {
            "source_raw_log": os.path.basename(input_path) if input_path else "unknown",
            "source_raw_log_created": ctime,
            "source_raw_log_modified": mtime,
            "decoded_with_dbc_file": os.path.basename(dbc_path) if dbc_path else "unknown",
            "number_of_frames_decoded": str(self.decoded_messages_counter),
            "raw_log_start_time": self.min_dt.isoformat(sep=' ') if self.min_dt else "",
            "raw_log_end_time": self.max_dt.isoformat(sep=' ') if self.max_dt else "",
            "raw_log_duration": str((self.max_dt - self.min_dt).total_seconds()) if self.min_dt and self.max_dt else "",
        }

        df.attrs.update(meta)
        # df.to_parquet(output_path, compression="zstd")
        df.to_parquet(
            output_path,
            compression="snappy",
            engine="pyarrow",
            use_dictionary=False
        )

        print(f"[ok] Parquet saved: {output_path} ({human_readable_size(os.path.getsize(output_path))})")
        print(f"[meta] Source file created: {ctime}")
        print(f"[meta] Source file modified: {mtime}")


# ========== CLI entrypoint ==========
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Decode Celka TXT logs into Parquet for PlotJuggler")
    parser.add_argument("--dbc", required=True, help="Path to .dbc file")
    parser.add_argument("--input", required=True, help="Path to .txt log file")
    parser.add_argument("--output", required=True, help="Path to output .parquet file")
    parser.add_argument("--ignore", nargs="*", default=[], help="IDs to ignore (hex, e.g. 0A 0B)")
    parser.add_argument("--verbose", action="store_true", help="Print extra corruption and decoding info")
    args = parser.parse_args()

    nkpl = NKPL()
    if args.ignore:
        nkpl.set_ignored_ids({int(x, 16) for x in args.ignore})

    nkpl.parse_and_decode(args.dbc, args.input, PRINT_ADDITIONAL_INFO=args.verbose)
    df = nkpl.to_dataframe()
    nkpl.export_parquet(df, args.output, args.dbc, args.input)
    print(f"[done] Parsed '{args.input}' → '{args.output}' successfully.")
