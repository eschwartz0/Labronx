"""Run with python src/example.py. All statistics here are fictional."""

import csv
from pathlib import Path


def main():
    sample_file = Path(__file__).resolve().parents[1] / "data" / "example_summaries.csv"
    print("Sample matchups only - these are not real MLB statistics.\n")
    with sample_file.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            key = (
                row["player"], row["stadium"], int(row["season"]),
                int(row["inning"]), row["pitcher_hand"], row["batter_hand"],
            )
            value = {
                "plate_appearances": int(row["plate_appearances"]),
                "home_runs": int(row["home_runs"]),
            }
            print("Matchup:", key)
            print("Statistics:", value, "\n")


if __name__ == "__main__":
    main()
