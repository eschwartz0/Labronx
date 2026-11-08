"""Separate-chaining hash table implemented without a dict as backing storage."""


class HashTable:
    def __init__(self, capacity=16, max_load_factor=0.75):
        if capacity < 1 or not 0 < max_load_factor <= 1:
            raise ValueError('capacity must be positive and load factor in (0, 1]')
        self._buckets = [[] for _ in range(capacity)]
        self._size = 0
        self._max_load_factor = max_load_factor

    def _hash(self, key):
        return hash(key) % len(self._buckets)

    def __len__(self):
        return self._size

    def load_factor(self):
        return self._size / len(self._buckets)

    def bucket_size(self, index):
        return len(self._buckets[index])

    def get(self, key, default=None):
        for stored_key, value in self._buckets[self._hash(key)]:
            if stored_key == key:
                return value
        return default

    def contains(self, key):
        return any(stored_key == key for stored_key, _ in self._buckets[self._hash(key)])

    def insert(self, key, value):
        bucket = self._buckets[self._hash(key)]
        for index, (stored_key, _) in enumerate(bucket):
            if stored_key == key:
                bucket[index] = (stored_key, value)
                return
        bucket.append((key, value))
        self._size += 1
        if self.load_factor() > self._max_load_factor:
            self.resize(len(self._buckets) * 2)

    def resize(self, capacity):
        if capacity < 1 or self._size / capacity > self._max_load_factor:
            raise ValueError('new capacity would exceed the configured load factor')
        old = self._buckets
        self._buckets = [[] for _ in range(capacity)]
        for bucket in old:
            for key, value in bucket:
                self._buckets[self._hash(key)].append((key, value))

    def items(self):
        for bucket in self._buckets:
            yield from bucket


# A descriptive alias for teammates importing the implementation by its full name.
SeparateChainingHashTable = HashTable
