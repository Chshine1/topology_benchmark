from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Self


@dataclass(frozen=True, slots=True)
class IntegralMatrix:
    flat: tuple[int, ...]
    columns: int

    @staticmethod
    def row_vector(values: Iterable[int]) -> Self:
        v = tuple(values)
        return IntegralMatrix(v, columns=len(v))

    @staticmethod
    def column_vector(values: Iterable[int]) -> Self:
        v = tuple(values)
        return IntegralMatrix(v, columns=1)

    @property
    def rows(self) -> int:
        return len(self.flat) // self.columns

    def at(self, i: int, j: int) -> int:
        return self.flat[i * self.columns + j]

    def _same_shape(self, other: Self) -> bool:
        return self.rows == other.rows and self.columns == other.columns

    def __add__(self, other):
        if not isinstance(other, IntegralMatrix):
            return NotImplemented
        if not self._same_shape(other):
            raise ValueError(
                f"shape mismatch: {self.rows}x{self.columns} vs {other.rows}x{other.columns}"
            )
        return IntegralMatrix(
            flat=tuple(a + b for a, b in zip(self.flat, other.flat)),
            columns=self.columns,
        )

    def __sub__(self, other):
        if not isinstance(other, IntegralMatrix):
            return NotImplemented
        if not self._same_shape(other):
            raise ValueError("shape mismatch")
        return IntegralMatrix(
            flat=tuple(a - b for a, b in zip(self.flat, other.flat)),
            columns=self.columns,
        )

    def __neg__(self):
        return IntegralMatrix(flat=tuple(-x for x in self.flat), columns=self.columns)

    def __mul__(self, other):
        if isinstance(other, int):
            return IntegralMatrix(flat=tuple(x * other for x in self.flat), columns=self.columns)

        if isinstance(other, IntegralMatrix):
            if self.columns != other.rows:
                raise ValueError(
                    f"cannot multiply {self.rows}x{self.columns} by {other.rows}x{other.columns}"
                )
            n, m, p = self.rows, self.columns, other.columns
            out = []
            for i in range(n):
                for j in range(p):
                    s = 0
                    for k in range(m):
                        s += self.at(i, k) * other.at(k, j)
                    out.append(s)
            return IntegralMatrix(flat=tuple(out), columns=p)

        return NotImplemented

    def __rmul__(self, other):
        if isinstance(other, int):
            return self.__mul__(other)
        return NotImplemented

    def __matmul__(self, other):
        if isinstance(other, IntegralMatrix):
            return self.__mul__(other)
        return NotImplemented

    def __rmatmul__(self, other):
        if isinstance(other, IntegralMatrix):
            return other.__mul__(self)
        return NotImplemented

    def det(self) -> int:
        if self.rows != self.columns:
            raise ValueError("determinant only defined for square matrices")
        n = self.rows
        m = [[Fraction(self.at(i, j)) for j in range(n)] for i in range(n)]
        det = Fraction(1)
        for col in range(n):
            pivot = next((r for r in range(col, n) if m[r][col] != 0), None)
            if pivot is None:
                return 0
            if pivot != col:
                m[col], m[pivot] = m[pivot], m[col]
                det = -det
            det *= m[col][col]
            for r in range(col + 1, n):
                if m[r][col] == 0:
                    continue
                factor = m[r][col] / m[col][col]
                for c in range(col, n):
                    m[r][c] -= factor * m[col][c]
        return int(det)

    def inverse(self) -> Self:
        if self.rows != self.columns:
            raise ValueError("only square matrices are invertible")
        n = self.rows
        d = self.det()
        if abs(d) != 1:
            raise ValueError(f"matrix is not unimodular (det = {d})")

        aug = [
            [Fraction(self.at(i, j)) for j in range(n)]
            + [Fraction(1 if i == j else 0) for j in range(n)]
            for i in range(n)
        ]
        for col in range(n):
            pivot = next((r for r in range(col, n) if aug[r][col] != 0), None)
            if pivot is None:
                raise ValueError("singular matrix")
            aug[col], aug[pivot] = aug[pivot], aug[col]
            pv = aug[col][col]
            aug[col] = [x / pv for x in aug[col]]
            for r in range(n):
                if r != col and aug[r][col] != 0:
                    f = aug[r][col]
                    aug[r] = [a - f * b for a, b in zip(aug[r], aug[col])]

        inv_flat = []
        for i in range(n):
            for j in range(n):
                v = aug[i][n + j]
                if v.denominator != 1:
                    raise ArithmeticError("non-integer inverse")
                inv_flat.append(int(v))
        return IntegralMatrix(flat=tuple(inv_flat), columns=n)

    def __truediv__(self, other):
        if not isinstance(other, IntegralMatrix):
            return NotImplemented
        return self @ other.inverse()

    def __floordiv__(self, other):
        return self.__truediv__(other)

    def __getitem__(self, key):
        if isinstance(key, tuple):
            if len(key) != 2:
                raise IndexError(f"expected 2 indices, got {len(key)}")
            row_key, col_key = key
        else:
            row_key, col_key = key, slice(None)

        n, m = self.rows, self.columns

        row_idx = self._resolve_index(row_key, n)
        col_idx = self._resolve_index(col_key, m)

        if isinstance(row_key, int) and isinstance(col_key, int):
            return self.at(row_idx[0], col_idx[0])

        flat = tuple(self.at(i, j) for i in row_idx for j in col_idx)
        return IntegralMatrix(flat=flat, columns=len(col_idx))

    @classmethod
    def _resolve_index(cls, key, size: int) -> list[int]:
        if isinstance(key, int):
            return [cls._normalize(key, size)]
        if isinstance(key, slice):
            return list(range(*key.indices(size)))
        if isinstance(key, (list, tuple)):
            return [cls._normalize(k, size) for k in key]
        raise TypeError(f"invalid index type: {type(key).__name__}")

    @staticmethod
    def _normalize(i: int, size: int) -> int:
        if i < 0:
            i += size
        if not 0 <= i < size:
            raise IndexError(f"index {i} out of range [0, {size})")
        return i


def smith_normal_decomposition(
    original: IntegralMatrix,
) -> tuple[IntegralMatrix, IntegralMatrix, IntegralMatrix]:  # U,D,V where UMV=D
    m, n = original.rows, original.columns

    a = [[original.at(i, j) for j in range(n)] for i in range(m)]

    l_trans = [[1 if i == j else 0 for j in range(m)] for i in range(m)]
    r_trans = [[1 if i == j else 0 for j in range(n)] for i in range(n)]

    def row_swap(i: int, j: int) -> None:
        if i == j:
            return
        a[i], a[j] = a[j], a[i]
        l_trans[i], l_trans[j] = l_trans[j], l_trans[i]

    def col_swap(i: int, j: int) -> None:
        if i == j:
            return
        for r in range(m):
            a[r][i], a[r][j] = a[r][j], a[r][i]
        for r in range(n):
            r_trans[r][i], r_trans[r][j] = r_trans[r][j], r_trans[r][i]

    def row_add(src: int, dst: int, k: int) -> None:
        if k == 0:
            return
        for c in range(n):
            a[dst][c] += k * a[src][c]
        for c in range(m):
            l_trans[dst][c] += k * l_trans[src][c]

    def col_add(src: int, dst: int, k: int) -> None:
        if k == 0:
            return
        for r in range(m):
            a[r][dst] += k * a[r][src]
        for r in range(n):
            r_trans[r][dst] += k * r_trans[r][src]

    def row_scale(i: int, k: int) -> None:
        if k == 1:
            return
        for c in range(n):
            a[i][c] *= k
        for c in range(m):
            l_trans[i][c] *= k

    t = 0
    while t < min(m, n):
        pr = pc = -1
        found = False
        for i in range(t, m):
            for j in range(t, n):
                if a[i][j] != 0:
                    pr, pc = i, j
                    found = True
                    break
            if found:
                break

        if not found:
            break

        if pr != t:
            row_swap(pr, t)
        if pc != t:
            col_swap(pc, t)

        for i in range(t + 1, m):
            while a[i][t] != 0:
                q = a[i][t] // a[t][t]
                if q:
                    row_add(t, i, -q)
                if a[i][t] != 0:
                    row_swap(t, i)

        for j in range(t + 1, n):
            while a[t][j] != 0:
                q = a[t][j] // a[t][t]
                if q:
                    col_add(t, j, -q)
                if a[t][j] != 0:
                    col_swap(t, j)

        if any(a[i][t] != 0 for i in range(t + 1, m)) or any(a[t][j] != 0 for j in range(t + 1, n)):
            continue

        if a[t][t] < 0:
            row_scale(t, -1)

        d = a[t][t]

        bad = False
        for i in range(t + 1, m):
            for j in range(t + 1, n):
                if a[i][j] % d != 0:
                    row_add(i, t, 1)
                    bad = True
                    break
            if bad:
                break

        if bad:
            continue

        t += 1

    d = IntegralMatrix(
        tuple(a[i][j] for i in range(m) for j in range(n)),
        columns=n,
    )

    u = IntegralMatrix(
        tuple(l_trans[i][j] for i in range(m) for j in range(m)),
        columns=m,
    )
    v = IntegralMatrix(
        tuple(r_trans[i][j] for i in range(n) for j in range(n)),
        columns=n,
    )

    return u, d, v
