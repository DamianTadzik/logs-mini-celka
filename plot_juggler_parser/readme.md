# Workflow z logami

1. Skopiuj pliki z karty SD na komputer, i zwróć uwagę na daty czy są dobre, jak nie to skoryguj za pomocą tego toola

python plot_juggler_parser/copy_logs.py \
--src F:/ \
--dst D:/Dane/workspace/logs-mini-celka/logs_storage/2025_12_07_workshop/raw_logs/

2. Dekoduj do PARQUET

python plot_juggler_parser/logs_parser.py \
--dbc D:/Dane/workspace/can-messages-mini-celka/can_messages_mini_celka.dbc \
--input D:/Dane/workspace/logs-mini-celka/logs_storage/2025_12_07_workshop/raw_logs/LOG002.TXT \
--output D:/Dane/workspace/logs-mini-celka/logs_storage/2025_12_07_workshop/raw_logs/LOG002.PARQUET \
--verbose

4. Podziel na mniejsze fragmenty

python plot_juggler_parser/parquet_cutter.py \
--input D:/Dane/workspace/logs-mini-celka/logs_storage/2025_10_23_zakrzowek/raw_logs/LOG002.PARQUET \
--output D:/Dane/workspace/logs-mini-celka/logs_storage/2025_10_23_zakrzowek/described_logs/test.PARQUET \
--start 10.0 \
--end 60.4

python plot_juggler_parser/parquet_cutter.py \
--input D:/Dane/workspace/logs-mini-celka/logs_storage/2025_12_06_workshop/raw_logs/LOG000.PARQUET \
--output D:/Dane/workspace/logs-mini-celka/logs_storage/2025_12_06_workshop/described_logs/SHORT.PARQUET \
--start 6.0 \
--end 706.0


5. Ewentualnie analizuj częstość ramek CAN

python plot_juggler_parser/analyze_logs.py \
--dbc D:/Dane/workspace/logs-mini-celka/logs_storage/2025_12_07_workshop/raw_logs/can_messages_mini_celka.dbc \ 
--input D:/Dane/workspace/logs-mini-celka/logs_storage/2025_12_07_workshop/raw_logs/LOG002.TXT \
--can-baud-rate 500000 \
--verbose

python plot_juggler_parser/analyze_logs.py \
--dbc F:/can_messages_mini_celka.dbc \
--input D:/Dane/workspace/logs-mini-celka/logs_storage/2025_12_06_workshop/raw_logs/LOG000.TXT \
--can-baud-rate 125000 \
--verbose

6.  Import to PJ with select colum as a timestamp

7. Convert GFR CSV to Parquet format

python plot_juggler_parser/csv_parser.py \
--input input.csv \
--output output.parquet \
--verbose

# TODO 
- description md file auto creation with cutter?
- pipelining 1 i 2 i 5
