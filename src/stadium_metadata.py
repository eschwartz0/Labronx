"""Resolve dimensions by actual venue ID and season, retaining source definitions."""
import csv
from pathlib import Path

DEFAULT_STADIUMS = Path(__file__).resolve().parents[1] / 'data/Stadium_dimensions.csv'


class StadiumMetadata:
    def __init__(self, path=DEFAULT_STADIUMS):
        self.rows = []
        with Path(path).open(newline='', encoding='utf-8-sig') as stream:
            for row in csv.DictReader(stream):
                # Older unsourced files remain unsupported rather than silently relabeled.
                if not row.get('stadium_id') or not row.get('dimensions_source_url'):
                    continue
                self.rows.append(row)

    def resolve(self, stadium_id, season=None):
        rows = [row for row in self.rows if int(row['stadium_id']) == stadium_id]
        if not rows:
            return None
        if season is None:
            # All-seasons analysis can still show a specific, explicitly labeled
            # latest available configuration instead of a blank stadium window.
            return max(rows, key=lambda row: int(row['valid_to_year']))
        matches = [row for row in rows
                   if int(row['valid_from_year']) <= season <= int(row['valid_to_year'])]
        if len(matches) > 1:
            raise ValueError(f'Overlapping stadium metadata for {stadium_id}/{season}')
        return matches[0] if matches else None


def fence_points(left, center, right, left_gap=None, right_gap=None):
    """Illustrative five-ray radial profile; it is not a surveyed fence outline."""
    from math import cos, sin, radians
    distances = [float(left), float(left_gap) if left_gap else (float(left)+float(center))/2,
                 float(center), float(right_gap) if right_gap else (float(right)+float(center))/2,
                 float(right)]
    return [(cos(radians(angle)) * distance, sin(radians(angle)) * distance)
            for angle, distance in zip([135, 112.5, 90, 67.5, 45], distances)]
