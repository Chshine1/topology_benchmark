class DisjointSetUnion:
    def __init__(self, size: int) -> None:
        if size < 0:
            raise ValueError("a disjoint set cannot have negative size")
        self._parent = list(range(size))

    def find(self, item: int) -> int:
        while self._parent[item] != item:
            self._parent[item] = self._parent[self._parent[item]]
            item = self._parent[item]
        return item

    def union(self, first: int, second: int) -> bool:
        first, second = self.find(first), self.find(second)
        if first == second:
            return False
        self._parent[second] = first
        return True


class OrientedDisjointSetUnion:
    __slots__ = ("_parent", "_weight", "_rank")

    def __init__(self, size: int) -> None:
        if size < 0:
            raise ValueError("a disjoint set cannot have negative size")
        self._parent = list(range(size))
        self._weight = [1] * size
        self._rank = [0] * size

    def find(self, item: int) -> tuple[int, int]:
        """Return (root, orientation of item relative to root)."""
        root = item
        total = 1
        while self._parent[root] != root:
            total *= self._weight[root]
            root = self._parent[root]

        current = item
        current_total = total
        while self._parent[current] != current:
            parent = self._parent[current]
            w = self._weight[current]
            self._parent[current] = root
            self._weight[current] = current_total
            current_total *= w
            current = parent

        return root, total

    def union(self, first: int, second: int, rel_orientation: int) -> bool:
        """Union, with orientation of `second` relative to `first` = rel_orientation."""
        root_f, w_f = self.find(first)
        root_s, w_s = self.find(second)

        if root_f == root_s:
            if w_f * rel_orientation != w_s:
                raise ValueError(f"inconsistent orientation: {w_f * rel_orientation} != {w_s}")
            return False

        link_weight = w_f * rel_orientation * w_s

        if self._rank[root_f] < self._rank[root_s]:
            self._parent[root_f] = root_s
            self._weight[root_f] = link_weight
        elif self._rank[root_f] > self._rank[root_s]:
            self._parent[root_s] = root_f
            self._weight[root_s] = link_weight
        else:
            self._parent[root_f] = root_s
            self._weight[root_f] = link_weight
            self._rank[root_s] += 1
        return True
