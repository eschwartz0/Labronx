import csv
from pathlib import Path
import random
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from analyzer import Analyzer, Dataset
from models import Filters, Summary


class AnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.pa_rows = [
            dict(game_pk=1, at_bat_number=1, batter_id=10, pitcher_id=20, stadium_id=100,
                 season=2025, inning=1, pitcher_hand='R', batter_hand='L', event='home_run',
                 plate_appearances=1, home_runs=1, home_team='NYY', away_team='BOS', inning_topbot='Bot'),
            dict(game_pk=1, at_bat_number=2, batter_id=11, pitcher_id=20, stadium_id=100,
                 season=2025, inning=1, pitcher_hand='R', batter_hand='R', event='walk',
                 plate_appearances=1, home_runs=0, home_team='NYY', away_team='BOS', inning_topbot='Bot'),
            dict(game_pk=2, at_bat_number=1, batter_id=10, pitcher_id=21, stadium_id=101,
                 season=2024, inning=10, pitcher_hand='L', batter_hand='L', event='field_out',
                 plate_appearances=1, home_runs=0, home_team='BOS', away_team='NYY', inning_topbot='Top'),
        ]
        self.write('yankees_plate_appearances.csv', self.pa_rows)
        self.write('game_venues.csv', [
            dict(game_pk=1, season=2025, game_date='2025-04-01', stadium_id=100, stadium='Home'),
            dict(game_pk=2, season=2024, game_date='2024-04-01', stadium_id=101, stadium='Away')])
        self.write('yankees_innings.csv', [
            dict(game_pk=1, season=2025, stadium_id=100, inning=1, yankees_runs=2),
            dict(game_pk=1, season=2025, stadium_id=100, inning=2, yankees_runs=0),
            dict(game_pk=2, season=2024, stadium_id=101, inning=10, yankees_runs=0)])

    def write(self, name, rows):
        with (self.folder / name).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def test_denominators_zero_innings_extra_innings_and_filters(self):
        analyzer = Analyzer(Dataset.load(self.folder), repeats=1)
        overall = analyzer.analyze()
        self.assertAlmostEqual(overall['hr_rate'], 1/3)
        self.assertAlmostEqual(overall['average_runs'], 2/3)
        self.assertAlmostEqual(overall['hr_inning_rate'], 1/3)
        self.assertEqual(overall['team_innings'], 3)
        selected = analyzer.analyze(Filters(batter_id=11, pitcher_hand='R'))
        self.assertEqual(selected['plate_appearances'], 1)
        self.assertEqual(selected['hr_rate'], 0)
        self.assertEqual(selected['team_innings'], 3)  # Team context ignores player/hand.
        empty = analyzer.analyze(Filters(batter_id=999))
        self.assertIsNone(empty['hr_rate'])
        self.assertEqual(empty['plate_appearances'], 0)
        no_innings = analyzer.analyze(Filters(inning=13))
        self.assertIsNone(no_innings['average_runs'])
        self.assertIsNone(no_innings['hr_inning_rate'])

    def test_chart_groups_respect_all_selected_filters(self):
        analyzer = Analyzer(Dataset.load(self.folder), repeats=1)
        result = analyzer.analyze(Filters(stadium_id=100))
        self.assertEqual(set(result['stadium_groups']), {100})
        self.assertEqual(set(result['inning_groups']), {1})
        result = analyzer.analyze(Filters(inning=1))
        self.assertEqual(set(result['inning_groups']), {1})
        result = analyzer.analyze(Filters(batter_id=999))
        self.assertEqual(result['stadium_groups'], {})
        self.assertEqual(result['inning_groups'], {})

    def test_identical_pa_deduplication_and_conflict_rejection(self):
        self.write('yankees_plate_appearances.csv', self.pa_rows + [self.pa_rows[0]])
        data = Dataset.load(self.folder)
        self.assertEqual(len(data.entries), 3)
        self.assertEqual(data.report['duplicate_pa_rows'], 1)
        self.write('yankees_plate_appearances.csv', self.pa_rows + [{**self.pa_rows[0], 'batter_id': 999}])
        with self.assertRaisesRegex(ValueError, 'Conflicting completed PA'):
            Dataset.load(self.folder)

    def test_runner_only_event_and_bad_venue_rejected(self):
        self.write('yankees_plate_appearances.csv', [{**self.pa_rows[0], 'event': 'caught_stealing_2b'}])
        with self.assertRaisesRegex(ValueError, 'Invalid completed-PA'):
            Dataset.load(self.folder)
        self.write('yankees_plate_appearances.csv', [{**self.pa_rows[0], 'stadium_id': 999}])
        with self.assertRaisesRegex(ValueError, 'venue'):
            Dataset.load(self.folder)


class DownloadedDataTests(unittest.TestCase):
    def test_existing_download_and_filtered_totals_against_csv_oracle(self):
        directory = Path(__file__).resolve().parents[1] / 'data/yankees_pa'
        if not (directory / 'yankees_plate_appearances.csv').exists():
            directory = Path('/Users/steven/PyCharmProjects/LaBronx/data/yankees_pa')
        if not directory.exists():
            self.skipTest('Local completed-PA CSVs are not installed')
        dataset = Dataset.load(directory)
        analyzer = Analyzer(dataset, repeats=1)
        expected = {2021: (6060, 222, 711), 2022: (6172, 254, 807),
                    2023: (5973, 219, 673), 2024: (6245, 237, 815), 2025: (6235, 274, 849)}
        for year, (pa, hr, runs) in expected.items():
            result = analyzer.analyze(Filters(season=year))
            self.assertEqual((result['plate_appearances'], result['home_runs']), (pa, hr))
            self.assertEqual(sum(row[3] for row in dataset.innings if row[1] == year), runs)
        rng = random.Random(3530)
        for _ in range(20):
            key, _ = rng.choice(dataset.entries)
            wanted = [value if rng.random() < .6 else None for value in key]
            result = analyzer.analyze(Filters(*wanted))
            oracle_pa = oracle_hr = 0
            for row_key, row_value in dataset.entries:
                if all(value is None or row_key[i] == value for i, value in enumerate(wanted)):
                    oracle_pa += row_value[0]
                    oracle_hr += row_value[1]
            self.assertEqual((result['plate_appearances'], result['home_runs']), (oracle_pa, oracle_hr))
            self.assertTrue(result['structures_match'])


if __name__ == '__main__':
    unittest.main()
