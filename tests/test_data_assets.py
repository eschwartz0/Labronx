import csv
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from benchmark_data import load_benchmark
from stadium_metadata import StadiumMetadata, fence_points


class StadiumTests(unittest.TestCase):
    def setUp(self):
        self.metadata = StadiumMetadata(ROOT / 'data/Stadium_dimensions.csv')

    def test_every_actual_yankees_venue_and_year_has_a_source(self):
        games = ROOT / 'data/yankees_pa/game_venues.csv'
        if not games.exists():
            games = Path('/Users/steven/PyCharmProjects/LaBronx/data/yankees_pa/game_venues.csv')
        with games.open() as stream:
            combinations = {(int(row['stadium_id']), int(row['season'])) for row in csv.DictReader(stream)}
        self.assertEqual(len(combinations), 111)
        for stadium, year in combinations:
            row = self.metadata.resolve(stadium, year)
            self.assertIsNotNone(row, (stadium, year))
            self.assertTrue(row['dimensions_source_url'].startswith('https://'))
            self.assertEqual(row['park_factor_metric'], 'Runs')
            self.assertEqual(row['park_factor_window'], str(year))
            self.assertTrue(row['park_factor_source_url'].startswith('https://'))

    def test_historical_changes_and_latest_labeled_configuration(self):
        self.assertEqual(self.metadata.resolve(2394, 2022)['Center'], '422')
        self.assertEqual(self.metadata.resolve(2394, 2025)['Center'], '412')
        self.assertEqual(self.metadata.resolve(2, 2021)['Left_Center'], '371')
        self.assertEqual(self.metadata.resolve(2, 2022)['Left_Center'], '398')
        self.assertEqual(self.metadata.resolve(2, 2025)['Left_Center'], '371')
        self.assertEqual(self.metadata.resolve(3313)['valid_from_year'], '2025')
        self.assertIsNone(self.metadata.resolve(999999, 2025))
        self.assertIsNone(self.metadata.resolve(3313, 2020))
        self.assertEqual(self.metadata.resolve(2735, 2024)['dimensions_basis'], 'Club-published distances')
        self.assertEqual(self.metadata.resolve(3313, 2024)['Park Factor'], '106')

    def test_different_distances_produce_different_fence_profiles(self):
        self.assertNotEqual(fence_points(318, 408, 314, 392, 364),
                            fence_points(309, 388, 299, 345, 378))
        self.assertEqual(len(fence_points(323, 411, 331)), 5)


class RealBenchmarkTests(unittest.TestCase):
    def test_real_pa_identities_and_original_yankees_totals(self):
        directory = ROOT / 'data/benchmark'
        if not (directory / 'mlb_plate_appearances.csv').exists():
            self.skipTest('Real MLB benchmark not installed')
        records, report = load_benchmark(directory)
        self.assertEqual(len(records), 181818)
        self.assertEqual(len({key for key, _ in records}), 181818)
        self.assertEqual(report['games'], 2429)
        self.assertTrue(report['all_30_team_totals_match'])
        yankees = [value for key, value in records if key[6] == 147]
        self.assertEqual((sum(v[0] for v in yankees), sum(v[1] for v in yankees)), (6060, 222))
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / 'preparation_report.json').write_bytes((directory / 'preparation_report.json').read_bytes())
            (folder / 'mlb_plate_appearances.csv').write_text('corrupt CSV')
            with self.assertRaisesRegex(ValueError, 'differs'):
                load_benchmark(folder)


if __name__ == '__main__':
    unittest.main()
