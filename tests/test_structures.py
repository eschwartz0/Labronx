import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from hash_table import HashTable
from red_black_tree import RedBlackTree
from models import Summary, build_structure


class CollisionKey(int):
    def __hash__(self):
        return 1


class StructureTests(unittest.TestCase):
    def test_collisions_resize_replacement_and_none(self):
        table = HashTable(capacity=2)
        for number in range(250):
            table.insert(CollisionKey(number), number * 2)
        self.assertGreater(len(table._buckets), 2)
        for number in range(250):
            self.assertEqual(table.get(CollisionKey(number)), number * 2)
        table.insert(CollisionKey(12), None)
        self.assertTrue(table.contains(CollisionKey(12)))
        self.assertIsNone(table.get(CollisionKey(12), 'missing'))
        self.assertEqual(len(table), 250)
        self.assertEqual(table.get(CollisionKey(-1), 'missing'), 'missing')
        self.assertFalse(table.contains(CollisionKey(-1)))

    def test_tree_invariants_for_sorted_reverse_and_random_input(self):
        random_keys = list(range(3000))
        random.Random(3530).shuffle(random_keys)
        for keys in (range(3000), reversed(range(3000)), random_keys):
            tree = RedBlackTree()
            for index, key in enumerate(keys):
                tree.insert(key, key * 2)
                if index % 137 == 0:
                    self.assertTrue(tree.validate())
            tree.insert(120, None)
            self.assertTrue(tree.contains(120))
            self.assertIsNone(tree.get(120, 'missing'))
            self.assertEqual(len(tree), 3000)
            self.assertEqual([key for key, _ in tree.items()], list(range(3000)))
            self.assertTrue(tree.validate())

    def test_random_operations_against_dictionary_oracle(self):
        rng = random.Random(42)
        table, tree, oracle = HashTable(), RedBlackTree(), {}
        for _ in range(10000):
            key = tuple(rng.randrange(5) for _ in range(6))
            value = rng.randrange(1000)
            table.insert(key, value)
            tree.insert(key, value)
            oracle[key] = value
            for structure in (table, tree):
                self.assertEqual(structure.get(key), oracle[key])
                self.assertTrue(structure.contains(key))
        self.assertEqual(dict(table.items()), oracle)
        self.assertEqual(dict(tree.items()), oracle)
        self.assertTrue(tree.validate())

    def test_100000_synthetic_updates_have_correct_distinct_count(self):
        # Synthetic stress test only; these are never reported as downloaded records.
        entries = [((i % 1000, 3313, 2025, 1, 'R', 'R'), Summary(1, int(i % 10 == 0)))
                   for i in range(100000)]
        table = build_structure(HashTable, entries)
        tree = build_structure(RedBlackTree, entries)
        self.assertEqual(len(table), 1000)
        self.assertEqual(dict(table.items()), dict(tree.items()))
        self.assertEqual(sum(value[0] for _, value in table.items()), 100000)
        self.assertEqual(sum(value[1] for _, value in tree.items()), 10000)
        self.assertTrue(tree.validate())


if __name__ == '__main__':
    unittest.main()
