import argparse
import pandas as pd
import sys
from pathlib import Path

GFR_COLMAP = {
    0:  "time_s",
    1:  "accel_x_mps2",
    2:  "accel_y_mps2",
    3:  "accel_z_mps2",
    4:  "pitch_deg",
    5:  "roll_deg",
    6:  "yaw_deg",
    7:  "course_deg",
    8:  "speed_mps",
    9:  "altitude_m",
    10: "latitude_deg",
    11: "longitude_deg",
    12: "horizontal_accuracy_m",
    13: "vertical_accuracy_m",
}

class CsvParser:
    def __init__(self, input_file, output_file, verbose=False):
        self.input_file = Path(input_file)
        self.output_file = Path(output_file)
        self.verbose = verbose

    def load_csv(self):
        if self.verbose:
            print(f"Loading CSV: {self.input_file}")

        try:
            self.df = pd.read_csv(
                self.input_file,
                header=0,
                usecols=range(len(GFR_COLMAP))
            )
        except Exception as e:
            print(f"CSV load error: {e}")
            sys.exit(1)

        # Enforce correct column count
        if self.df.shape[1] != len(GFR_COLMAP):
            print(f"Invalid CSV format: expected {len(GFR_COLMAP)} columns, got {self.df.shape[1]}")
            sys.exit(1)

        # Rename by index (ignore CSV header names)
        self.df.columns = [GFR_COLMAP[i] for i in range(len(GFR_COLMAP))]

        # Force numeric (hard)
        self.df = self.df.apply(pd.to_numeric, errors="coerce")

    def export_parquet(self):
        if self.verbose:
            print(f"Writing Parquet: {self.output_file}")

        try:
            self.df.to_parquet(self.output_file, engine="pyarrow", index=False)
        except Exception as e:
            print(f"Parquet export error: {e}")
            sys.exit(1)

    def run(self):
        self.load_csv()
        self.export_parquet()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert GFR CSV to Parquet")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    
    CsvParser(args.input, args.output, args.verbose).run()
