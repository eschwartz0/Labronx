"""CSV validation, custom-map integration, and historical Yankees statistics."""
import argparse
import csv
from dataclasses import dataclass
import json
from pathlib import Path
from time import perf_counter_ns

from benchmarks import benchmark
from benchmark_data import load_benchmark
from hash_table import HashTable
from red_black_tree import RedBlackTree
from models import Filters, Summary, matches, build_structure

PA_EVENTS = {
    'single', 'double', 'triple', 'home_run', 'walk', 'intent_walk', 'hit_by_pitch',
    'strikeout', 'strikeout_double_play', 'field_out', 'force_out',
    'grounded_into_double_play', 'double_play', 'triple_play', 'field_error',
    'fielders_choice', 'fielders_choice_out', 'sac_fly', 'sac_bunt',
    'sac_fly_double_play', 'sac_bunt_double_play', 'catcher_interf', 'other_out',
}
DEFAULT_DATA = Path(__file__).resolve().parents[1] / 'data' / 'yankees_pa'


def read_csv(path):
    with path.open(newline='', encoding='utf-8-sig') as stream:
        yield from csv.DictReader(stream)


@dataclass
class Dataset:
    entries: list
    innings: list
    players: dict
    venues: dict
    seasons: list
    inning_numbers: list
    report: dict

    @classmethod
    def load(cls, directory=DEFAULT_DATA):
        directory = Path(directory)
        venues_by_game, venue_names = {}, {}
        for row in read_csv(directory / 'game_venues.csv'):
            game = int(row['game_pk'])
            value = (int(row['stadium_id']), int(row['season']))
            if game in venues_by_game and venues_by_game[game] != value:
                raise ValueError(f'Conflicting venue metadata for game {game}')
            venues_by_game[game] = value
            stadium = value[0]
            stamp = row['game_date']
            if stadium not in venue_names or stamp > venue_names[stadium][0]:
                venue_names[stadium] = (stamp, row['stadium'])
        pa_seen, entries, pa_innings, hr_innings = {}, [], set(), set()
        players, seasons, inning_numbers = {}, set(), set()
        source_rows = 0
        for row in read_csv(directory / 'yankees_plate_appearances.csv'):
            source_rows += 1
            game, at_bat = int(row['game_pk']), int(row['at_bat_number'])
            if at_bat < 1:
                raise ValueError(f'Invalid completed-PA identifier: {(game, at_bat)}')
            key = (int(row['batter_id']), int(row['stadium_id']), int(row['season']),
                   int(row['inning']), row['pitcher_hand'], row['batter_hand'])
            event = row['event']
            value = Summary(int(row['plate_appearances']), int(row['home_runs']))
            if event not in PA_EVENTS or value != Summary(1, int(event == 'home_run')):
                raise ValueError(f'Invalid completed-PA outcome: {(game, at_bat)}')
            if venues_by_game.get(game) != (key[1], key[2]):
                raise ValueError(f'Missing/conflicting game venue: {game}')
            batting = row['away_team'] if row['inning_topbot'] == 'Top' else (
                row['home_team'] if row['inning_topbot'] == 'Bot' else None)
            if batting != 'NYY' or key[3] < 1 or key[4] not in ('L', 'R') or key[5] not in ('L', 'R'):
                raise ValueError(f'Invalid Yankees batting context: {(game, at_bat)}')
            identity = (game, at_bat)
            fingerprint = tuple(sorted(row.items()))
            if identity in pa_seen:
                if pa_seen[identity] != fingerprint:
                    raise ValueError(f'Conflicting completed PA: {identity}')
                continue
            pa_seen[identity] = fingerprint
            entries.append((key, value))
            players[key[0]] = f'Batter {key[0]}'
            seasons.add(key[2])
            inning_numbers.add(key[3])
            pa_innings.add((game, key[3]))
            if value.home_runs:
                hr_innings.add((game, key[3]))
        seen_innings, innings = {}, []
        for row in read_csv(directory / 'yankees_innings.csv'):
            game, inning = int(row['game_pk']), int(row['inning'])
            stadium, season, runs = int(row['stadium_id']), int(row['season']), int(row['yankees_runs'])
            if venues_by_game.get(game) != (stadium, season) or inning < 1 or runs < 0:
                raise ValueError(f'Invalid inning context: {(game, inning)}')
            value = (stadium, season, inning, runs, (game, inning) in hr_innings)
            if (game, inning) in seen_innings:
                if seen_innings[(game, inning)] != value:
                    raise ValueError(f'Conflicting inning: {(game, inning)}')
                continue
            seen_innings[(game, inning)] = value
            innings.append(value)
            inning_numbers.add(inning)
        if pa_innings - set(seen_innings):
            raise ValueError('Some batting PA have no corresponding played team inning')
        if not entries or not innings:
            raise ValueError('No completed plate appearances or played team innings loaded')
        names_path = directory / 'players.csv'
        if names_path.exists():
            for row in read_csv(names_path):
                player = int(row['batter_id'])
                if player in players and row['player_name'].strip():
                    players[player] = row['player_name'].strip()
        report = {'source_pa_rows': source_rows, 'completed_pa_records': len(entries),
                  'duplicate_pa_rows': source_rows - len(entries),
                  'unique_summary_keys': len({key for key, _ in entries}),
                  'games': len({game for game, _ in pa_seen}),
                  'home_runs': sum(value.home_runs for _, value in entries),
                  'team_innings': len(innings), 'team_runs': sum(row[3] for row in innings),
                  'note': 'Input is the existing completed-PA extract, not raw pitches. '
                          'Pitch deduplication cannot be checked from this extract.'}
        return cls(entries, innings, players,
                   {stadium: name for stadium, (_, name) in venue_names.items()},
                   sorted(seasons), sorted(inning_numbers), report)


def summarize(structure, filters):
    """Traverse custom-map entries to support wildcard filters; no hidden dict query."""
    total = Summary()
    stadium_groups, inning_groups = {}, {}
    for key, value in structure.items():
        if matches(key, filters):
            total = Summary(total[0] + value[0], total[1] + value[1])
            old = stadium_groups.get(key[1], Summary())
            stadium_groups[key[1]] = Summary(old[0] + value[0], old[1] + value[1])
            old = inning_groups.get(key[3], Summary())
            inning_groups[key[3]] = Summary(old[0] + value[0], old[1] + value[1])
    return total, stadium_groups, inning_groups


class Analyzer:
    def __init__(self, dataset, repeats=3, benchmark_dir=None):
        self.dataset = dataset
        if benchmark_dir is not None and (Path(benchmark_dir) / 'mlb_plate_appearances.csv').exists():
            self.hash_table = build_structure(HashTable, dataset.entries)
            self.tree = build_structure(RedBlackTree, dataset.entries)
            self.tree.validate()
            if dict(self.hash_table.items()) != dict(self.tree.items()):
                raise ValueError('Yankees application summaries disagree')
            records, self.benchmark_report = load_benchmark(benchmark_dir)
            self.benchmark_hash, self.benchmark_tree, self.metrics = benchmark(records, repeats=repeats)
            self.metrics.update(self.benchmark_report)
            self.metrics['meets_100000_stored_entries'] = min(
                len(self.benchmark_hash), len(self.benchmark_tree)) >= 100000
        else:
            self.hash_table, self.tree, self.metrics = benchmark(dataset.entries, repeats=repeats)
            self.metrics['scope'] = 'Yankees 2021–2025 matchup summaries'
            self.metrics['scenario'] = 'Matchup summary index'

    def analyze(self, filters=Filters()):
        query_times, results = {}, []
        for name, structure in [('hash', self.hash_table), ('tree', self.tree)]:
            start = perf_counter_ns()
            result = summarize(structure, filters)
            query_times[name] = (perf_counter_ns() - start) / 1e6
            results.append(result)
        if results[0] != results[1]:
            raise ValueError('Data structures disagree for the selected filters')
        total, stadium_groups, inning_groups = results[0]
        played = [row for row in self.dataset.innings
                  if (filters.stadium_id is None or row[0] == filters.stadium_id)
                  and (filters.season is None or row[1] == filters.season)
                  and (filters.inning is None or row[2] == filters.inning)]
        return {'plate_appearances': total[0], 'home_runs': total[1],
                'hr_rate': total[1] / total[0] if total[0] else None,
                'team_innings': len(played),
                'average_runs': sum(row[3] for row in played) / len(played) if played else None,
                'hr_inning_rate': sum(row[4] for row in played) / len(played) if played else None,
                'stadium_groups': stadium_groups, 'inning_groups': inning_groups,
                'query_ms': query_times, 'structures_match': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--out', type=Path, help='Save validation/benchmark JSON')
    parser.add_argument('--benchmark-dir', type=Path, help='Validated MLB-wide PA benchmark folder')
    parser.add_argument('--require-records', type=int, default=0,
                        help='Fail if actual completed-PA benchmark inputs fall below this count')
    args = parser.parse_args()
    dataset = Dataset.load(args.data_dir)
    analyzer = Analyzer(dataset, benchmark_dir=args.benchmark_dir or args.data_dir.parent / 'benchmark')
    result = analyzer.analyze()
    report = {'data': dataset.report, 'benchmarks': analyzer.metrics,
              'overall_statistics': {key: value for key, value in result.items()
                                     if key not in ('stadium_groups', 'inning_groups')}}
    output = json.dumps(report, indent=2) + '\n'
    print(output)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding='utf-8')
    if analyzer.metrics['input_records'] < args.require_records:
        parser.exit(1, f"Actual benchmark PA records: {analyzer.metrics['input_records']:,}; required: {args.require_records:,}\n")


if __name__ == '__main__':
    main()
