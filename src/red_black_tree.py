"""Insertion-only red-black map with parent links, rotations and recoloring."""


class _Node:
    __slots__ = ('key', 'value', 'red', 'left', 'right', 'parent')

    def __init__(self, key, value, parent=None):
        self.key, self.value, self.parent = key, value, parent
        self.red = True
        self.left = self.right = None


class RedBlackTree:
    def __init__(self):
        self._root = None
        self._size = 0

    def __len__(self):
        return self._size

    def _find(self, key):
        node = self._root
        while node is not None:
            if key == node.key:
                return node
            node = node.left if key < node.key else node.right
        return None

    def get(self, key, default=None):
        node = self._find(key)
        return default if node is None else node.value

    def contains(self, key):
        return self._find(key) is not None

    def insert(self, key, value):
        parent, node = None, self._root
        while node is not None:
            parent = node
            if key == node.key:
                node.value = value
                return
            node = node.left if key < node.key else node.right
        node = _Node(key, value, parent)
        if parent is None:
            self._root = node
        elif key < parent.key:
            parent.left = node
        else:
            parent.right = node
        self._size += 1
        self._fix_insert(node)

    def _rotate_left(self, node):
        pivot = node.right
        node.right = pivot.left
        if pivot.left is not None:
            pivot.left.parent = node
        pivot.parent = node.parent
        if node.parent is None:
            self._root = pivot
        elif node is node.parent.left:
            node.parent.left = pivot
        else:
            node.parent.right = pivot
        pivot.left, node.parent = node, pivot

    def _rotate_right(self, node):
        pivot = node.left
        node.left = pivot.right
        if pivot.right is not None:
            pivot.right.parent = node
        pivot.parent = node.parent
        if node.parent is None:
            self._root = pivot
        elif node is node.parent.left:
            node.parent.left = pivot
        else:
            node.parent.right = pivot
        pivot.right, node.parent = node, pivot

    def _fix_insert(self, node):
        while node.parent is not None and node.parent.red:
            parent = node.parent
            grandparent = parent.parent
            if parent is grandparent.left:
                uncle = grandparent.right
                if uncle is not None and uncle.red:
                    parent.red = uncle.red = False
                    grandparent.red = True
                    node = grandparent
                else:
                    if node is parent.right:
                        node = parent
                        self._rotate_left(node)
                    node.parent.red = False
                    node.parent.parent.red = True
                    self._rotate_right(node.parent.parent)
            else:
                uncle = grandparent.left
                if uncle is not None and uncle.red:
                    parent.red = uncle.red = False
                    grandparent.red = True
                    node = grandparent
                else:
                    if node is parent.left:
                        node = parent
                        self._rotate_right(node)
                    node.parent.red = False
                    node.parent.parent.red = True
                    self._rotate_left(node.parent.parent)
        self._root.red = False

    def items(self):
        stack, node = [], self._root
        while stack or node is not None:
            while node is not None:
                stack.append(node)
                node = node.left
            node = stack.pop()
            yield node.key, node.value
            node = node.right

    def validate(self):
        """Raise AssertionError on broken BST, parent, color or black-height invariants."""
        if self._root is None:
            assert self._size == 0
            return True
        assert not self._root.red and self._root.parent is None
        count = 0

        def walk(node, lower, upper, parent):
            nonlocal count
            if node is None:
                return 1
            count += 1
            assert node.parent is parent
            assert lower is None or lower < node.key
            assert upper is None or node.key < upper
            if node.red:
                assert node.left is None or not node.left.red
                assert node.right is None or not node.right.red
            left = walk(node.left, lower, node.key, node)
            right = walk(node.right, node.key, upper, node)
            assert left == right
            return left + int(not node.red)

        walk(self._root, None, None, None)
        assert count == self._size
        return True
