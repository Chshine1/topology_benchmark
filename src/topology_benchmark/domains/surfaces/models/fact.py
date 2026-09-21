from dataclasses import dataclass

from .object import EdgeRef


@dataclass(frozen=True, slots=True)
class ComponentFacts:
    polygon_indices: tuple[int, ...]
    orientable: bool
    euler_characteristic: int
    boundary_count: int

    @property
    def genus(self) -> int:
        numerator = 2 - self.boundary_count - self.euler_characteristic
        return numerator // 2 if self.orientable else numerator

    @property
    def first_betti_number(self) -> int:
        if self.orientable:
            return 2 * self.genus + max(0, self.boundary_count - 1)
        return self.genus - 1 + self.boundary_count


@dataclass(frozen=True, slots=True)
class SurfaceFacts:
    components: tuple[ComponentFacts, ...]

    @property
    def euler_characteristic(self) -> int:
        return sum(component.euler_characteristic for component in self.components)

    @property
    def boundary_components(self) -> int:
        return sum(component.boundary_count for component in self.components)


@dataclass(frozen=True, slots=True)
class DimensionOneHomologyElement:
    edges_representative: tuple[tuple[int, EdgeRef], ...]
    order: int | None


@dataclass(frozen=True, slots=True)
class CellularHomology:
    h0_rank: int
    h1_basis: tuple[DimensionOneHomologyElement, ...]
    h2_rank: int
