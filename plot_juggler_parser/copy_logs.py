#!/usr/bin/env python3
import argparse
from pathlib import Path
import shutil
import sys
import os
from datetime import datetime

def format_time(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

def parse_time(s: str) -> float:
    """Parse 'YYYY-MM-DD HH:MM:SS' to timestamp."""
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").timestamp()

def human_readable_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes / 1024**2:.2f} MB"
    else:
        return f"{size_bytes / 1024**3:.2f} GB"

def set_creation_time_windows(path: Path, timestamp: float):
    """Windows only: set creation time using pywin32."""
    try:
        import pywintypes, win32file, win32con
        handle = win32file.CreateFile(
            str(path),
            win32con.GENERIC_WRITE,
            0,
            None,
            win32con.OPEN_EXISTING,
            win32con.FILE_ATTRIBUTE_NORMAL,
            None,
        )
        win_time = pywintypes.Time(timestamp)
        win32file.SetFileTime(handle, win_time, None, None)
        handle.close()
    except ImportError:
        print(f"\tpywin32 not installed; creation time unchanged.")
    except Exception as e:
        print(f"\tfailed to set creation time: {e}")

def copy_logs(src: Path, dest: Path) -> int:
    if not src.is_dir():
        raise ValueError(f"Source path does not exist or is not a directory: {src}")

    dest.mkdir(parents=True, exist_ok=True)
    count = 0

    for file in src.iterdir():
        if file.suffix.lower() not in (".txt", ".dbc"):
            continue

        dst_file = dest / file.name

        if dst_file.exists():
            ans = input(f"File '{file.name}' already exists. [o]verwrite / [s]kip / [r]ename? ").strip().lower()
            if ans == "s":
                print("\tSkipped.")
                continue
            elif ans == "r":
                new_name = input("\tEnter new filename: ").strip()
                if not new_name:
                    print("\tInvalid name, skipping.")
                    continue
                dst_file = dest / new_name

        shutil.copy2(file, dst_file)
        count += 1

        stat = file.stat()
        print(f"\n{file.name}")
        print(f"  ├─ size: {human_readable_size(stat.st_size)}")
        print(f"  ├─ created: {format_time(stat.st_ctime)}")
        print(f"  └─ modified: {format_time(stat.st_mtime)}")

        if file.suffix.lower() == ".txt":
            ans = input(f"\tChange timestamps? [y/N]: ").strip().lower()
            if ans == "y":
                try:
                    cr = input(f"\tEnter creation date (YYYY-MM-DD HH:MM:SS) or leave empty in order to set to now:\n\r\t").strip()
                    mo = input(f"\tEnter modification date (YYYY-MM-DD HH:MM:SS) or leave empty in order to set to now:\n\r\t").strip()

                    cr_ts = parse_time(cr) if cr else None
                    mo_ts = parse_time(mo) if mo else None

                    # Apply modification time
                    if mo_ts:
                        os.utime(dst_file, (mo_ts, mo_ts))

                    # Apply creation time (Windows only)
                    if cr_ts and os.name == "nt":
                        set_creation_time_windows(dst_file, cr_ts)
                    elif cr_ts:
                        print(f"\tCreation time change not supported on this OS.")

                    print(f"\ttimestamps updated.")
                except Exception as e:
                    print(f"\tfailed to update: {e}")

    return count

# ========== CLI entrypoint ==========
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy .TXT and .DBC files while preserving timestamps.")
    parser.add_argument("--src", required=True, type=Path, help="Source directory (e.g. F:/)")
    parser.add_argument("--dst", required=True, type=Path, help="Destination directory")
    args = parser.parse_args()

    try:
        copied = copy_logs(args.src, args.dst)
        print(f"\n[info] Copied {copied} files to: {args.dst.resolve()}")
    except Exception as e:
        print(f"[error] {e}", file=sys.stderr)
        sys.exit(1)
