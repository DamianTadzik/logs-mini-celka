# AI Coding Agent Instructions for logs-mini-celka

## Project Overview
This codebase analyzes CAN bus logs from a "mini celka" system. It converts raw TXT logs to Parquet format using DBC definitions, cuts time slices, analyzes frame frequencies, and visualizes in PlotJuggler.

**Architecture:**
- `plot_juggler_parser/`: Core Python tools for log processing
- `logs_storage/`: Dated folders with raw logs (TXT, DBC) and processed data
- `legacy_code_archive/`: MATLAB code for older workflows
- `GFR_parser/`: Specialized CSV parsing (currently minimal)

**Data Flow:**
- Raw TXT logs → Decode to Parquet (logs_parser.py) → Visualize in PlotJuggler
- Raw TXT logs → Optionally cut Parquet segments (parquet_cutter.py) → Visualize in PlotJuggler
- Raw TXT logs → Analyze stats (analyze_logs.py) for frequency, jitter, bus load

## Key Workflows
- **Setup:** Use venv with `requirements.txt` (includes cantools, pandas, pyarrow)
- **Copy Logs:** `python plot_juggler_parser/copy_logs.py --src F:/ --dst logs_storage/YYYY_MM_DD_location/raw_logs/`
- **Decode:** `python plot_juggler_parser/logs_parser.py --dbc path/to/.dbc --input LOG.TXT --output LOG.parquet --verbose`
- **Cut Segments:** `python plot_juggler_parser/parquet_cutter.py --input LOG.parquet --output segment.parquet --start 10.0 --end 60.4`
- **Analyze:** `python plot_juggler_parser/analyze_logs.py --dbc .dbc --input LOG.TXT --can-baud-rate 500000 --verbose`

## Conventions
- **Time Column:** Use `seconds_since_start` (float) for temporal data
- **DBC Files:** CAN message definitions in `can_messages_mini_celka.dbc`
- **Log Format:** TXT with `HH:MM:SS,mmm;ID;DATA` lines
- **Output:** Parquet with decoded signals, metadata preserved
- **Naming:** Scripts use argparse with `--input`, `--output`, `--dbc` flags
- **Error Handling:** Scripts print progress, warn on corruption, exit on critical errors

## Patterns
- **DBC Decoding:** Use cantools.database.load() then db.decode_message()
- **Timestamp Parsing:** Regex `^\d{2}:\d{2}:\d{2},\d{3}$` for HH:MM:SS,mmm
- **Metadata:** Store in Parquet attrs dict (e.g., df.attrs['dbc_path'] = args.dbc)
- **CAN ID Validation:** 2-char hex strings only
- **File Organization:** Raw logs in `raw_logs/`, processed in `described_logs/`

## Dependencies
- python-can, cantools for CAN handling
- pandas, pyarrow for data processing
- PlotJuggler 3.12+ for visualization (external tool)

Reference: `plot_juggler_parser/readme.md` for detailed command examples.