from attrs import field, frozen, validators


@frozen
class VertexPartitionConfig:
    attempts: int = field(default=30, validator=validators.ge(1))
    easy_mark_count: int = field(default=4, validator=validators.ge(1))
    hard_mark_count: int = field(default=5, validator=validators.ge(1))
    hard_from: int = field(default=6, validator=validators.ge(1))


@frozen
class VertexDegreeConfig:
    attempts: int = field(default=30, validator=validators.ge(1))


@frozen
class CurvatureOrderConfig:
    attempts: int = field(default=30, validator=validators.ge(1))
    exact_margin: float = field(default=8.0, validator=validators.ge(0.0))
    visible_margin: int = field(default=6, validator=validators.ge(0))


@frozen
class SeamMatchConfig:
    attempts: int = field(default=30, validator=validators.ge(1))
    candidate_count: int = field(default=3, validator=validators.ge(1))


@frozen
class CellDistanceConfig:
    attempts: int = field(default=30, validator=validators.ge(1))
    edge_cells_from: int = field(default=4, validator=validators.ge(1))
    vertex_cells_from: int = field(default=7, validator=validators.ge(1))
    candidate_limit: int = field(default=24, validator=validators.ge(1))


@frozen
class PolyhedralDomainConfig:
    vertex_partition: VertexPartitionConfig = field(factory=VertexPartitionConfig)
    vertex_degree: VertexDegreeConfig = field(factory=VertexDegreeConfig)
    curvature_order: CurvatureOrderConfig = field(factory=CurvatureOrderConfig)
    seam_match: SeamMatchConfig = field(factory=SeamMatchConfig)
    cell_distance: CellDistanceConfig = field(factory=CellDistanceConfig)
