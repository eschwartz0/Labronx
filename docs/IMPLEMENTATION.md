# Running the completed desktop integration

From the PyCharm project root:

```bash
python3 -m pip install -r requirements.txt
python3 src/gui.py
python3 -m unittest discover -s tests -v
python3 src/analyzer.py --require-records 100000 --out data/benchmark/validation_benchmarks.json
```

Tkinter must be available in the selected Python interpreter. The local Python 3.14
installation already has Tkinter and Matplotlib. The GUI can also receive
`--data-dir PATH` pointing at another folder containing the three processed CSVs.
No download runs on startup and no fictional example data is loaded.

## Files and public interface

- `src/hash_table.py`: custom separate-chaining `HashTable` with resizing.
- `src/red_black_tree.py`: custom `RedBlackTree` with rotations/recoloring and
  `validate()` for its BST, parent-link, color and black-height invariants.
- `src/models.py`: `Summary`, `Filters`, and the shared input construction loop.
- `src/analyzer.py`: CSV validation, queries, chart groups and team inning statistics.
- `src/benchmarks.py`: construction/lookup timing and deep retained object memory.
- `src/charts.py`: Matplotlib drawing functions used in the GUI's top two panels.
- `src/gui.py`: original Tkinter layout connected to the backend; background loading
  keeps CSV validation and benchmark builds off the Tk event thread.
- `data/yankees_pa/players.csv`: 75 batter names sourced by MLB player ID from
  the public MLB people API. Existing PA, venue and inning CSVs are preserved.

Both structures expose `insert(key, value)`, `get(key, default=None)`,
`contains(key)`, `items()`, and `len(structure)`. Inserting an existing key replaces
its value without increasing the entry count. `None` is a valid stored value.
Keys in this application are:

```python
(batter_id, stadium_id, season, inning, pitcher_hand, batter_hand)
```

Values are immutable `Summary(plate_appearances, home_runs)` tuples, accessible by
position or named field. The shared construction loop consumes every deduplicated
completed PA and adds `(1, is_home_run)` to the corresponding summary. Neither
structure uses a built-in dict for backing storage. Temporary dictionaries are used
for CSV validation/metadata, chart grouping and independent equality checks.

## Filters and charts

Player and stadium menus use IDs behind readable names. Season menus contain only
the data's seasons plus All seasons. Extra innings come from the data. Batter side
means the actual L/R side of the PA; a switch hitter can appear on either side.

Analyze computes the selected historical HR/PA rate and sample size through both
custom structures and refuses to show results if they disagree. Team average runs
and percentage of innings with a HR use stadium/season/inning filters only, as stated
in the window. Player and hand filters do not remove whole team innings.

All six filters automatically refresh both charts and statistics after a short 100 ms
coalescing delay; Analyze remains available for a manual refresh. Both charts honor
every selected PA filter, including stadium and inning. Selecting one stadium produces
its matching bar; selecting one inning produces that inning's bar. The stadium chart
shows up to seven matching venues ranked by sample size. Both charts include sample
sizes, show zero HR correctly, and handle empty samples.

Run `python3 tests/gui_dynamic_smoke.py` for the native regression check. It changes
each filter without clicking Analyze, checks both chart canvases and statistics,
and verifies rapid changes coalesce into one query.

## Statistics

- HR rate = matching HR / matching completed PA. Includes walks, HBP and sacrifices
  in the PA denominator. Empty PA selections show N/A.
- Average runs = Yankees runs across selected played batting innings / number of
  those innings. Zero-run innings are included.
- Team innings with HR = count(selected innings with at least one Yankees HR) /
  selected played team innings. Multiple HR in one inning count once.
- Unplayed home halves are absent from the original linescore extraction; played
  walk-off halves and extra innings remain included.

The loader checks completed outcomes, duplicate/conflicting PA identities, Yankees
batting context, game-ID venue joins, and PA-to-inning joins. It operates on the
existing processed CSVs, which have no pitch_number; it cannot reconstruct or check
deduplication of raw pitch records from those files.

## Benchmark interpretation

The GUI now measures both structures on 181,818 real completed MLB plate appearances
from the full 2021 regular season. Each benchmark entry has a unique composite key:

```python
(batter_id, stadium_id, season, inning, pitcher_hand, batter_hand,
 batting_team_id, game_pk, at_bat_number)
```

Appending the team and PA identifiers makes this a **PA record index**, with 181,818
actual inputs and 181,818 stored entries in each structure. This meets both a
100,000-input requirement and a 100,000-stored-record interpretation. The same
input contains 75,272 distinct team/matchup summary keys; those are reported separately.
The GUI's Yankees statistics still use the original six-field summary key and the
existing 30,685 PAs / 12,816 summaries across 2021–2025. The benchmark panel labels
both scopes. Do not describe the record-index benchmark as a timing of a wildcard
GUI query or a six-field summary-only index.

Construction timings include all real PA inserts and exclude CSV reading and source
validation. They are medians of three builds, alternating which structure goes first.
Exact lookup timings use the same seeded 2,000-key workload with 50% hits and 50%
misses, taking the median of five batches and reporting microseconds per lookup.
Full Yankees wildcard query times are separate in the status line.

Memory is a deep retained Python object-graph estimate including each structure's
keys and values, with references/cycles counted once within each structure. It is
not RSS or peak allocation. Timing is performed without allocation tracing.

The real MLB CSV is loaded only when its preparation manifest is complete, all
30 official team PA/HR comparisons pass, its SHA-256 matches, and every PA identity
is unique. `--require-records 100000` now succeeds with the installed benchmark.
No synthetic, repeated or fictional rows are counted toward the requirement.

## Stadium metadata

`data/Stadium_dimensions.csv` now contains 156 sourced stadium/year rows, covering
all 111 venue/season combinations and all 36 venue IDs in the actual Yankees games.
Rows include applicable season, source URLs, retrieval date, five fence distances
where available, the distance definition, and sourced single-season Runs park factors
(both batter sides, all conditions, 100 average).

Most distances come from Baseball Savant's per-season Dimensions table. They are
Statcast-listed distances and can differ from posted signs or old venue API values.
The R column supplies the Runs park factor; the separate general Park Factor column
is not mislabeled as Runs. The preserved source-table extracts and exact definitions
are in `data/stadium_sources/`. Source links in the window open the relevant data.

Journey Bank Ballpark 2024 has no Savant dimension row. Its row uses the club's
published 323/411/331 distances, corroborated by MLB's report of the 2017 renovation;
its absent gap distances are left blank. The schematic interpolates the missing gaps
for display only. It does not claim surveyed geometry. The row records this exception.

Selecting a stadium and season updates the distances, field profile and park factor.
The source's seasonal measurements are preserved, including small year-to-year
measurement differences. With All seasons selected, the window explicitly labels
the latest available configuration; it does not imply that configuration applied
throughout the entire analysis. With All stadiums selected, Yankee Stadium is labeled
as a preview. Historical aliases (such as Minute Maid Park) resolve by venue ID/year.

## Data preparation and provenance

The runtime CSVs, validation manifest, and source reports are included in the
repository. No Statcast downloader is required to run the application.

The original Yankees files are preserved. The MLB benchmark was prepared by
downloading unfiltered raw Statcast CSVs in small date ranges and compressing source caches.
The preparation process deduplicates pitches by `(game_pk, at_bat_number, pitch_number)`, checks conflicts,
and derives completed PA by `(game_pk, at_bat_number)` using completed batting
outcomes rather than every last pitch or runner event. Raw PA Result and Pitch Result
filters are blank. It checks coverage of 2,429 actually played games, excludes cancelled
schedule entries, and reconciles PA/HR for every team to the official MLB season totals.

The preserved source has 745,619 CSV rows, 712,320 unique pitch keys and 33,299 identical
duplicate pitch rows. These are distinct from its 181,818 completed PA records.
Per-team season reconciliation does not independently certify every per-game outcome.
The benchmark preparation report preserves source hashes and all reconciliation rows.

The processed CSV is complete; running the GUI does not download data. Acquisition
tools, raw compressed CSV caches, and redundant per-game/trial exports stay local.
`python3 scripts/prepare_stadium_metadata.py` can regenerate the stadium CSV from
the bundled source-table JSON snapshots and game/venue metadata.

## Validation performed

The original nine tests plus four data-asset tests verify collisions, resizing,
replacement, missing keys, tree invariants, 100,000 synthetic stress updates (never
counted as real data), CSV conflict rejection, inning denominators, chart filtering,
real-data totals, all 111 stadium/year joins, historical configuration changes,
geometry changes, 181,818 unique real benchmark identities, and manifest tamper rejection.
The native Tkinter smoke test covers actual player filters, chart refreshes, empty
samples, historical stadium selections, source labels and the 100,000-record benchmark.
