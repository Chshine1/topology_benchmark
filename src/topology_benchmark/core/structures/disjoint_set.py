class DisjointSet:
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
