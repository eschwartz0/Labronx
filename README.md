# Yankees Matchup Analyzer

Team LaBronx's UF COP3530 desktop project, built with Python, Tkinter/ttk,
Matplotlib, a custom separate-chaining hash table, and a custom red-black tree.

## Run after cloning

```bash
python3 -m pip install -r requirements.txt
python3 src/gui.py
```

Use a Python interpreter with Tkinter available. The data is bundled; running the
app requires no Statcast download. Changing a filter refreshes both charts and
statistics automatically, including the stadium preview. There are no Analyze
or View Stadium buttons; choose your filters to update the results.

## Bundled application data

- `data/yankees_pa/yankees_plate_appearances.csv`: 30,685 completed Yankees PAs, 2021–2025.
- `data/yankees_pa/yankees_innings.csv`: played Yankees batting innings and scoring.
- `data/yankees_pa/game_venues.csv`: actual venues joined by game ID.
- `data/yankees_pa/players.csv`: batter IDs and names.
- `data/Stadium_dimensions.csv`: sourced season-specific distances and runs park factors.
- `data/benchmark/mlb_plate_appearances.csv`: 181,818 real completed MLB PAs from 2021.

The benchmark also requires its bundled `preparation_report.json`, which validates
CSV integrity and records official PA/HR reconciliation for all 30 teams. Each
custom structure stores 181,818 distinct benchmark records. 

Yankees analysis uses
the separate five-season dataset. 

Source snapshots and validation reports are bundled.

## Check correctness

```bash
python3 -m unittest discover -s tests -v
python3 src/analyzer.py --require-records 100000
python3 tests/gui_dynamic_smoke.py
```

This test suite includes 27 tests for both custom structures,
chart output, and automatic filter/stadium updates. The filter tests use Tcl
variables/timers without opening a window, so the suite needs no desktop session.

On Windows, use `py` instead of `python3` for the commands above.

See [implementation and data provenance](docs/IMPLEMENTATION.md)
for key definitions, statistics, measurement methods, and stadium sources.

`src/example.py` and `data/example_summaries.csv` are an explicitly fictional format
example; the application uses the real CSVs above.
