"""Load a provenance-checked MLB benchmark without changing Yankees app filters."""
import csv
import hashlib
import json
from pathlib import Path

from models import Summary


def load_benchmark(directory):
    directory = Path(directory)
    path = directory / 'mlb_plate_appearances.csv'
    manifest = json.loads((directory / 'preparation_report.json').read_text())
    payload = path.read_bytes()
    if not manifest.get('complete') or not manifest.get('all_teams_match'):
        raise ValueError('MLB benchmark has not passed official PA/HR reconciliation')
    if hashlib.sha256(payload).hexdigest() != manifest['output_sha256']:
        raise ValueError('MLB benchmark CSV differs from its validated source manifest')
    identities, entries, summary_keys = set(), [], set()
    with path.open(newline='', encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            identity = (int(row['game_pk']), int(row['at_bat_number']))
            if identity in identities:
                raise ValueError(f'Duplicate benchmark completed PA: {identity}')
            identities.add(identity)
            context = (int(row['batter_id']), int(row['stadium_id']), int(row['season']),
                       int(row['inning']), row['pitcher_hand'], row['batter_hand'],
                       int(row['batting_team']))
            value = Summary(int(row['plate_appearances']), int(row['home_runs']))
            if value != Summary(1, int(row['event'] == 'home_run')):
                raise ValueError(f'Invalid benchmark PA value: {identity}')
            summary_keys.add(context)
            # Record-index scenario stores every real PA as its own entry. Team ID
            # prevents inter-team contamination and game/PA IDs guarantee uniqueness.
            entries.append((context + identity, value))
    if len(entries) != manifest['completed_pa_records'] or len(entries) < 100000:
        raise ValueError('Benchmark requires at least 100,000 validated real completed PAs')
    report = {'scope': manifest['scope'], 'record_unit': 'completed plate appearance',
              'scenario': 'PA record index (context + team ID + game ID + PA number)',
              'source_rows': manifest['source_rows'],
              'deduplicated_pitch_keys': manifest['deduplicated_pitch_keys'],
              'input_pa_records': len(entries), 'unique_record_keys': len(identities),
              'unique_matchup_summary_keys': len(summary_keys),
              'games': manifest['downloaded_games'], 'all_30_team_totals_match': True,
              'source_sha256': manifest['output_sha256']}
    return entries, report
