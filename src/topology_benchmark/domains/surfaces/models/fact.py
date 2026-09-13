from dataclasses import dataclass

from .object import EdgeRef


@dataclass(frozen=True, slots=True)
class ComponentFacts:
    polygons: tuple[int, ...]
    orientable: bool
    euler_characteristic: int
    boundary_components: int
    genus: int

    @property
    def first_betti_number(self) -> int:
        if self.orientable:
            return 2 * self.genus + max(0, self.boundary_components - 1)
        return self.genus - 1 + self.boundary_components


@dataclass(frozen=True, slots=True)
class SurfaceFacts:
    components: tuple[ComponentFacts, ...]
    vertex_count: int
    edge_count: int
    face_count: int

    @property
    def euler_characteristic(self) -> int:
        return self.vertex_count - self.edge_count + self.face_count

    @property
    def boundary_components(self) -> int:
        return sum(component.boundary_components for component in self.components)


@dataclass(frozen=True, slots=True)
class CellularHomology:
    """``relations`` are d2 columns in the fundamental ``cycle_basis`` of ker(d1).

    ``smith_coordinate_map`` converts coordinates in that basis to the Smith basis.
    """

    edge_basis: tuple[EdgeRef, ...]
    cycle_basis: tuple[str, ...]
    relations: tuple[tuple[int, ...], ...]
    smith_diagonal: tuple[int, ...]
    smith_basis: tuple[tuple[int, ...], ...]
    smith_coordinate_map: tuple[tuple[int, ...], ...]
    h0_rank: int
    h1_rank: int
    h1_torsion: tuple[int, ...]
    h2_rank: int
