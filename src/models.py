"""Shared key/value contract for both custom maps (IDs, never display names)."""
from typing import NamedTuple, Optional

MatchupKey = tuple[int, int, int, int, str, str]


class Summary(NamedTuple):
    plate_appearances: int = 0
    home_runs: int = 0


class Filters(NamedTuple):
    batter_id: Optional[int] = None
    stadium_id: Optional[int] = None
    season: Optional[int] = None
    inning: Optional[int] = None
    pitcher_hand: Optional[str] = None
    batter_hand: Optional[str] = None


def matches(key, filters, ignore=None):
    return all(wanted is None or index == ignore or key[index] == wanted
               for index, wanted in enumerate(filters))


def build_structure(factory, entries):
    structure = factory()
    for key, value in entries:
        old = structure.get(key, Summary())
        structure.insert(key, Summary(old.plate_appearances + value.plate_appearances,
                                      old.home_runs + value.home_runs))
    return structure
