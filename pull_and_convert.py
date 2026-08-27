import subprocess
import argparse
import os
import time

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





# MsgPack decoding

def open_msgpack(path):
    """
    Create an iterator over consecutive MsgPack objects.
    strict_map_key=False is required because schema IDs in the header
    are integer dictionary keys.
    """
    f = open(path, "rb")
    unpacker = msgpack.Unpacker(f, raw=False, strict_map_key=False)
    return f, unpacker

def flatten_dict(d, prefix="", out=None):
    """
    Flatten nested dictionaries:
        {"signals": {"Speed": 2.5}}
    becomes:
        {"signals/Speed": 2.5}
    """
    if out is None:
        out = {}

    for key, value in d.items():
        name = f"{prefix}/{key}" if prefix else str(key)

        if isinstance(value, dict):
            flatten_dict(value, name, out)
        else:
            out[name] = value
    return out

def flatten_record(record):
    """
    Flatten one decoded log record into Parquet-style columns.

    Every record type gets its own namespace:
        can/...
        control_cycle/...
        newtype/...

    CAN signals are additionally namespaced by CAN message name:
        can/signals/<message>/<signal>
    """
    out = {}

    record_type = record.get("type", "unknown")

    for key, value in record.items():

        if key == "type":
            continue

        if record_type == "can" and key == "message":
            continue

        # CAN signals need one more hierarchy level:
        # can/signals/<message>/<signal>
        if key == "signals" and record_type == "can":
            message = record.get("message")
            if isinstance(value, dict) and message is not None:
                flatten_dict(value, prefix=f"{record_type}/signals/{message}", out=out)
            continue

        prefix = f"{record_type}/{key}"

        if isinstance(value, dict):
            flatten_dict(value, prefix=prefix, out=out)
        else:
            out[prefix] = value

    return out

def decode_schema_record(pkt, header):
    """
    Decode [schema_id, value0, value1, ...] using the header.
    Returns None if the record cannot be decoded.
    """
    if header is None:
        return None
    if not isinstance(pkt, list) or not pkt:
        return None
    
    schemas = header["schemas"]
    schema_id = pkt[0]
    schema = schemas.get(schema_id)

    if schema is None:
        return None

    fields = schema["fields"]
    values = pkt[1:]

    if len(fields) != len(values):
        return None
    return {"type": schema["type"], **dict(zip(fields, values))}


def discover_parquet_schema(src):
    header = None
    samples = {}

    f, unpacker = open_msgpack(src)

    try:
        try:
            first = next(unpacker)
        except StopIteration:
            return None, pa.schema([])

        if isinstance(first, dict) and first.get("type") == "header":
            header = first
            packets = unpacker
        else:
            # No header -> the first packet is still normal log data.
            packets = iter([first, *unpacker])

        for pkt in packets:
            primary_timestamp = None

            # Normal dictionary record.
            if isinstance(pkt, dict):
                record = pkt
                # Headerless/self-describing records use timestamp_s directly.
                primary_timestamp = record.get("timestamp_s")
            # Compact record: decode only if header exists.
            elif isinstance(pkt, list):
                record = decode_schema_record(pkt, header)
                if record is None:
                    continue
                # By convention: [schema_id, primary_timestamp, ...]
                if len(pkt) > 1:
                    primary_timestamp = pkt[1]
            else:
                continue

            flat = flatten_record(record)

            # Common time axis for the whole Parquet file.
            if primary_timestamp is not None:
                flat["timestamp_s"] = primary_timestamp

            for name, value in flat.items():
                if value is None:
                    continue
                # For now one example value is enough to inspect
                # what schema discovery produces.
                if name not in samples:
                    samples[name] = value

    finally:
        f.close()

    fields = []

    for name in sorted(samples):
        value = samples[name]

        try:
            arrow_type = pa.array([value]).type
        except Exception as exc:
            print(
                f"WARNING: cannot infer type of '{name}' "
                f"from {value!r}: {exc}"
            )
            continue

        fields.append(
            pa.field(name, arrow_type, nullable=True)
        )

    return header, pa.schema(fields)


def decode_msgpack_to_parquet(src, dst, batch_size=10000, cb=None):
    total_size = os.path.getsize(src)
    # Discover the schema from the file
    header, arrow_schema = discover_parquet_schema(src)
    # print("\nHEADER:")
    # print(header)
    # print("\nPARQUET SCHEMA:")
    # print(arrow_schema)
    writer = pq.ParquetWriter(
        dst,
        arrow_schema,
        compression="snappy",
        use_dictionary=True,
    )
    rows = []
    f, unpacker = open_msgpack(src)
    try:
        for pkt in unpacker:
            # Skip header.
            if isinstance(pkt, dict) and pkt.get("type") == "header":
                continue
            primary_timestamp = None
            # Normal dictionary record.
            if isinstance(pkt, dict):
                record = pkt
                primary_timestamp = record.get("timestamp_s")
            # Compact schema record.
            elif isinstance(pkt, list):
                record = decode_schema_record(pkt, header)
                # Headerless compact records cannot be decoded.
                if record is None:
                    continue
                if len(pkt) > 1:
                    primary_timestamp = pkt[1]
            else:
                continue

            row = flatten_record(record)
            if primary_timestamp is not None:
                row["timestamp_s"] = primary_timestamp
            rows.append(row)

            # Write one batch.
            if len(rows) >= batch_size:
                table = pa.Table.from_pylist(rows, schema=arrow_schema)
                writer.write_table(table)
                rows.clear()
                if cb:
                    cb(unpacker.tell(), total_size)

        # Write remaining rows.
        if rows:
            table = pa.Table.from_pylist(rows, schema=arrow_schema)
            writer.write_table(table)

    finally:
        f.close()
        writer.close()
    if cb:
        cb(total_size, total_size, done=True)

def format_size(size):
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.0f}M"
    if size >= 1024:
        return f"{size / 1024:.0f}K"
    return f"{size}B"
def format_time(seconds):
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"


if __name__ == "__main__":
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

    print("Decoding logs locally...")
    for fname in os.listdir(args.local_dir):
        if not fname.endswith(".msgpack"):
            continue
        src = os.path.join(args.local_dir, fname)
        dst = os.path.join(args.parquet_dir, fname.replace(".msgpack", ".parquet"))

        start_time = time.time()
        def progress_cb(current, total, done=False):
            elapsed = time.time() - start_time
            percent = 100.0 * current / total if total else 0.0
            parquet_size = (os.path.getsize(dst) if os.path.exists(dst) else 0)

            if done:
                time_text = format_time(elapsed)
            else:
                if current > 0:
                    eta = elapsed * (total - current) / current
                    time_text = f"{format_time(eta)} ETA"
                else:
                    time_text = "--:-- ETA"
            print("\r\033[K"
                f"{fname} "
                f"{percent:3.0f}% "
                f"{format_size(current)}/{format_size(total)} "
                f"-> {os.path.basename(dst)} "
                f"{format_size(parquet_size)} "
                f"{time_text}",
                end="",
                flush=True,
            )
            if done:
                print()

        decode_msgpack_to_parquet(src, dst, cb=progress_cb)

    print("Done!")
