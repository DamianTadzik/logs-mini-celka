import argparse
import subprocess
import os
import msgpack
import pyarrow as pa
import pyarrow.parquet as pq


def pull_logs(host, remote_dir, local_dir):
    os.makedirs(local_dir, exist_ok=True)

    cmd = [
        "scp",
        "-r",
        f"{host}:/{remote_dir}/*.msgpack",
        local_dir
    ]
    subprocess.run(cmd, check=True)


def delete_remote_logs(host, remote_dir):
    cmd = [
        "ssh",
        host,
        f"rm -f /{remote_dir}/*.msgpack"
    ]
    subprocess.run(cmd, check=True)


def decode_msgpack_to_rows(path):
    rows = []

    with open(path, "rb") as f:
        unpacker = msgpack.Unpacker(f, raw=False)
        for pkt in unpacker:
            row = {}

            # timestamp
            row["timestamp"] = pkt.get("timestamp")

            # flatten brzanpi
            for group, data in pkt.get("brzanpi", {}).items():
                if not isinstance(data, dict):
                    continue
                for k, v in data.items():
                    if isinstance(v, (int, float)):
                        row[f"{group}/{k}"] = v

            rows.append(row)

    return rows


def write_parquet(rows, out_path):
    if not rows:
        return

    table = pa.Table.from_pylist(rows)
    pq.write_table(
        table,
        out_path,
        compression="snappy"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--remote-dir", required=True)
    ap.add_argument("--local-dir", required=True)
    ap.add_argument("--parquet-dir", required=True)
    ap.add_argument("--delete-remote", action="store_true")
    args = ap.parse_args()

    os.makedirs(args.parquet_dir, exist_ok=True)

    print("Pulling logs from RPi...")
    pull_logs(args.host, args.remote_dir, args.local_dir)

    if args.delete_remote:
        print("Deleting logs on RPi...")
        delete_remote_logs(args.host, args.remote_dir)

    print("Decoding logs...")
    for fname in os.listdir(args.local_dir):
        if not fname.endswith(".msgpack"):
            continue

        src = os.path.join(args.local_dir, fname)
        dst = os.path.join(
            args.parquet_dir,
            fname.replace(".msgpack", ".parquet")
        )

        rows = decode_msgpack_to_rows(src)
        write_parquet(rows, dst)

        print(f" -  {fname} → {os.path.basename(dst)}")

    print("... done!")


if __name__ == "__main__":
    main()
