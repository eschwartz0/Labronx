"""Reproducible workloads; CSV parsing is excluded from construction timings."""
import gc
import random
import sys
from statistics import median
from time import perf_counter_ns

from hash_table import HashTable
from red_black_tree import RedBlackTree
from models import build_structure


def retained_size(root):
    """Deep retained Python object bytes, including keys/values, with cycles deduped.

    Count each structure independently even when its input keys are shared. This is
    an object-graph estimate, not process RSS or peak allocation. Classes/methods
    and the source dataset are excluded unless retained by the structure itself.
    """
    seen, pending, total = set(), [root], 0
    while pending:
        obj = pending.pop()
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        total += sys.getsizeof(obj)
        if isinstance(obj, dict):
            pending.extend(obj.keys())
            pending.extend(obj.values())
        elif isinstance(obj, (tuple, list, set)):
            pending.extend(obj)
        elif hasattr(obj, '__dict__'):
            pending.append(vars(obj))
        elif hasattr(type(obj), '__slots__'):
            pending.extend(getattr(obj, name) for name in type(obj).__slots__)
    return total


def benchmark(entries, repeats=3, lookup_count=2000):
    if repeats < 1 or lookup_count < 1:
        raise ValueError('repeats and lookup_count must be positive')
    factories = {'hash': HashTable, 'tree': RedBlackTree}
    maps, timings = {}, {name: [] for name in factories}
    for repeat in range(repeats):
        order = list(factories) if repeat % 2 == 0 else list(reversed(factories))
        for name in order:
            gc.collect()
            start = perf_counter_ns()
            structure = build_structure(factories[name], entries)
            elapsed = perf_counter_ns() - start
            timings[name].append(elapsed)
            maps[name] = structure
    maps['tree'].validate()
    # Dicts are used only as independent correctness oracles, never map storage.
    if dict(maps['hash'].items()) != dict(maps['tree'].items()):
        raise ValueError('Hash table and red-black tree summaries disagree')
    keys = sorted(key for key, _ in maps['tree'].items())
    rng = random.Random(3530)
    workload = []
    for index in range(lookup_count):
        if keys and index % 2 == 0:
            workload.append(keys[rng.randrange(len(keys))])
        else:
            workload.append((-index - 1, -1, -1, -1, '?', '?'))
    lookup_times = {name: [] for name in factories}
    for repeat in range(5):
        order = list(factories) if repeat % 2 == 0 else list(reversed(factories))
        for name in order:
            get = maps[name].get
            start = perf_counter_ns()
            for key in workload:
                get(key)
            lookup_times[name].append((perf_counter_ns() - start) / lookup_count)
    metrics = {
        name: {'construction_ms': median(timings[name]) / 1e6,
               'lookup_us': median(lookup_times[name]) / 1000,
               'memory_bytes': retained_size(maps[name]),
               'stored_entries': len(maps[name])}
        for name in factories
    }
    metrics['input_records'] = len(entries)
    metrics['unique_keys'] = len(keys)
    metrics['meets_100000_input_records'] = len(entries) >= 100000
    metrics['method'] = (
        f'Construction median of {repeats} builds; exact lookup median of 5 batches '
        f'of {lookup_count} keys (50% hits for nonempty data). '
        'Memory is deep retained Python object bytes including keys/values; not RSS. '
        'CSV reading and validation excluded. Full filtered-query time is separate.')
    return maps['hash'], maps['tree'], metrics
