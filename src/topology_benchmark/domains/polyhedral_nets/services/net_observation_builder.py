from attrs import evolve

from topology_benchmark.domains.polyhedral_nets.models.net import (
    EdgePair,
    FaceCorner,
    NetEdge,
    PolyhedralNet,
)
from topology_benchmark.domains.polyhedral_nets.services.polyhedral_cell_graph_analyzer import (
    MarkedEdge,
    MarkedFace,
    MarkedNetCell,
    MarkedVertex,
)


class NetObservationBuilder:
    def mark_cells(
        self,
        net: PolyhedralNet,
        hints: tuple[EdgePair, ...],
        first: MarkedNetCell,
        second: MarkedNetCell,
    ) -> PolyhedralNet:
        corners = []
        edges = []
        faces = []
        for cell, label in ((first, "A"), (second, "B")):
            if isinstance(cell, MarkedVertex):
                corners.append((FaceCorner(cell.face, cell.corner), label))
            elif isinstance(cell, MarkedEdge):
                edges.append((NetEdge(cell.face, cell.edge), label))
            else:
                assert isinstance(cell, MarkedFace)
                faces.append((cell.face, label))
        return evolve(
            net,
            seam_hints=hints,
            corner_labels=tuple(corners),
            edge_labels=tuple(edges),
            face_labels=tuple(faces),
        )

    def cell_name(self, cell: MarkedNetCell, label: str) -> str:
        if isinstance(cell, MarkedVertex):
            return f"the folded vertex containing corner {label}"
        if isinstance(cell, MarkedEdge):
            return f"the folded edge containing boundary edge {label}"
        return f"face {label}"
