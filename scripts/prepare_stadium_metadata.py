#!/usr/bin/env python3
"""Build year-specific stadium CSV from preserved official source-table extracts."""
import argparse
import csv
import json
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--games', type=Path, default=ROOT / 'data/yankees_pa/game_venues.csv')
    parser.add_argument('--out', type=Path, default=ROOT / 'data/Stadium_dimensions.csv')
    args = parser.parse_args()
    sources = ROOT / 'data/stadium_sources'
    dimensions = json.loads((sources / 'savant_dimensions_2021_2025.json').read_text())
    factors = json.loads((sources / 'savant_runs_factors_2021_2025.json').read_text())
    aliases, names, required = {}, {}, set()
    with args.games.open(newline='') as stream:
        for row in csv.DictReader(stream):
            stadium, year = int(row['stadium_id']), int(row['season'])
            aliases[(stadium, year)] = row['stadium']
            names[stadium] = row['stadium']
            required.add((stadium, year))
    fields = ['stadium_id', 'Ballpark', 'valid_from_year', 'valid_to_year', 'Left',
              'Left_Center', 'Center', 'Right_Center', 'Right', 'Deepest', 'Park Factor',
              'park_factor_metric', 'park_factor_window', 'park_factor_batter_side',
              'park_factor_conditions', 'dimensions_basis', 'dimensions_source_url',
              'park_factor_source_url', 'retrieved_date', 'notes']
    rows = []
    for year_text, values in dimensions['seasons'].items():
        year = int(year_text)
        year_factors = {row[0]: row[1] for row in factors['seasons'][year_text]}
        for stadium, left, lc, center, rc, right, deepest in values:
            if stadium not in names:
                continue
            row = dict(zip(fields, [''] * len(fields)))
            row.update(stadium_id=stadium, Ballpark=aliases.get((stadium, year), names[stadium]),
                       valid_from_year=year, valid_to_year=year, Left=left, Left_Center=lc,
                       Center=center, Right_Center=rc, Right=right, Deepest=deepest,
                       dimensions_basis='Statcast-listed fence distances',
                       dimensions_source_url='https://baseballsavant.mlb.com/leaderboard/statcast-park-factors?'
                       + urlencode({'type': 'dimensions', 'year': year}),
                       retrieved_date=dimensions['retrieved_date'],
                       notes='Source distances may differ from posted signage. Diagram is a schematic, not a surveyed fence map.')
            if stadium in year_factors:
                row.update({'Park Factor': year_factors[stadium], 'park_factor_metric': 'Runs',
                            'park_factor_window': str(year), 'park_factor_batter_side': 'Both',
                            'park_factor_conditions': 'All',
                            'park_factor_source_url': 'https://baseballsavant.mlb.com/leaderboard/statcast-park-factors?'
                            + urlencode({'type': 'year', 'year': year, 'batSide': '',
                                         'stat': 'index_runs', 'condition': 'All', 'rolling': 1, 'parks': 'all'})})
            rows.append(row)
    # This special 2024 venue has no row in Savant's 2024 dimensions table.
    # Use the club's published distances, corroborated by MLB's 2017 renovation article.
    # Do not copy its 2025 Statcast measurement backward to 2024.
    year = 2024
    source = 'https://www.mlbdraftleague.com/williamsport/ballpark/atoz'
    fallback = {field: '' for field in fields}
    fallback.update(stadium_id=2735, Ballpark=aliases.get((2735, year), 'Journey Bank Ballpark'),
                    valid_from_year=year, valid_to_year=year, Left=323, Center=411, Right=331,
                    dimensions_basis='Club-published distances', dimensions_source_url=source,
                    retrieved_date=dimensions['retrieved_date'],
                    notes='Club A-to-Z distances; MLB reports this configuration introduced in 2017: '
                    'https://www.mlb.com/amp/news/did-you-know-little-league-classic-c249582588.html. '
                    'No 2024 Statcast dimension row. Gap distances unavailable; diagram interpolates only for illustration.')
    factor = next(row[1] for row in factors['seasons']['2024'] if row[0] == 2735)
    fallback.update({'Park Factor': factor, 'park_factor_metric': 'Runs', 'park_factor_window': '2024',
                     'park_factor_batter_side': 'Both', 'park_factor_conditions': 'All',
                     'park_factor_source_url': 'https://baseballsavant.mlb.com/leaderboard/statcast-park-factors?type=year&year=2024&stat=index_runs&rolling=1&parks=all'})
    rows.append(fallback)
    available = {(int(row['stadium_id']), int(row['valid_from_year'])) for row in rows}
    if required - available:
        raise ValueError(f'Missing actual Yankees venue/seasons: {sorted(required-available)}')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: (int(row['stadium_id']), int(row['valid_from_year']))))
    report = {'stadium_rows': len(rows), 'unique_venues': len(names),
              'required_yankees_venue_seasons': len(required), 'missing': [],
              'source_retrieved_date': dimensions['retrieved_date'],
              'definition': dimensions['definition'],
              'special_case': 'Journey Bank Ballpark 2024 uses club-published distances; no Savant yearly dimension row.'}
    (sources / 'coverage_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
