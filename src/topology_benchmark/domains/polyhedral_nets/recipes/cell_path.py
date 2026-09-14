from random import Random
from typing import override

from topology_benchmark.domains.polyhedral_nets.abstractions import (
    IPolyhedralNetGenerator,
    IPolyhedralNetRepresentation,
)
from topology_benchmark.domains.polyhedral_nets.config import CellDistanceConfig
from topology_benchmark.domains.polyhedral_nets.generation.completion import (
    NetQuestionCertifier,
    ObservableCompletionEnumerator,
)
from topology_benchmark.domains.polyhedral_nets.models.net import EdgePair, PolyhedralFolding
from topology_benchmark.domains.polyhedral_nets.recipes.base import (
    PolyhedralProblemDraft,
    PolyhedralProblemRecipe,
)
from topology_benchmark.domains.polyhedral_nets.services.net_observation_builder import (
    NetObservationBuilder,
)
from topology_benchmark.domains.polyhedral_nets.services.polyhedral_cell_graph_analyzer import (
    MarkedEdge,
    MarkedFace,
    MarkedNetCell,
    MarkedVertex,
    PolyhedralCellGraphAnalyzer,
)
from topology_benchmark.domains.polyhedral_nets.services.polyhedral_net_analyzer import (
    PolyhedralNetAnalyzer,
)


class CellDistanceProblemRecipe(PolyhedralProblemRecipe):
    id = "cell-distance"
    count_paths = False

    def __init__(
        self,
        analyzer: PolyhedralNetAnalyzer,
        graph: PolyhedralCellGraphAnalyzer,
        certifier: NetQuestionCertifier,
        observations: NetObservationBuilder,
        config: CellDistanceConfig,
        net_generator: IPolyhedralNetGenerator,
        completions: ObservableCompletionEnumerator,
        representation: IPolyhedralNetRepresentation,
    ) -> None:
        super().__init__(net_generator, completions, representation)
        self._analyzer = analyzer
        self._graph = graph
        self._certifier = certifier
        self._observations = observations
        self.config = config
        self.attempts = config.attempts

    @override
    def _build(
        self,
        folding: PolyhedralFolding,
        solutions: tuple[tuple[EdgePair, ...], ...],
        difficulty: int,
        rng: Random,
    ) -> PolyhedralProblemDraft | None:
        kinds = ("face",) if difficulty < self.config.edge_cells_from else ("face", "edge")
        if difficulty >= self.config.vertex_cells_from:
            kinds = ("face", "edge", "vertex")
        cells: list[MarkedNetCell] = []
        if "face" in kinds:
            cells.extend(MarkedFace(face) for face in range(len(folding.net.faces)))
        if "edge" in kinds:
            cells.extend(MarkedEdge(edge.face, edge.edge) for edge in folding.net.boundary_edges)
        if "vertex" in kinds:
            cells.extend(
                MarkedVertex(corner.face, corner.corner)
                for vertex in self._analyzer.analyze(folding).vertices
                for corner in (rng.choice(vertex),)
            )
        candidates = [
            (first, second) for index, first in enumerate(cells) for second in cells[index + 1 :]
        ]
        rng.shuffle(candidates)
        prefer_zero = bool(rng.randrange(2))
        preferred = [
            pair
            for pair in candidates
            if (self._graph.statistics(folding.net, folding.seams, *pair)[0] == 0) == prefer_zero
        ]
        for first, second in (preferred or candidates)[: self.config.candidate_limit]:

            def answer(
                seams: tuple[EdgePair, ...],
                a: MarkedNetCell = first,
                b: MarkedNetCell = second,
            ) -> int:
                distance, paths = self._graph.statistics(folding.net, seams, a, b)
                return paths if self.count_paths else distance

            certified = self._certifier.certify(folding.seams, solutions, answer, difficulty)
            if certified is None:
                continue
            hints, value = certified
            a = self._observations.cell_name(first, "A")
            b = self._observations.cell_name(second, "B")
            prompt = (
                f"How many shortest vertex paths in the folded 1-skeleton connect {a} to {b}? "
                "Path length is the number of edges. Distinct paths have different vertex "
                "sequences; each common vertex gives one zero-edge path."
                if self.count_paths
                else f"What is the minimum number of edges in a vertex path through the folded "
                f"1-skeleton connecting {a} to {b}?"
            )
            return PolyhedralProblemDraft(
                prompt,
                value,
                self._observations.mark_cells(folding.net, hints, first, second),
            )
        return None


class ShortestPathCountProblemRecipe(CellDistanceProblemRecipe):
    id = "cell-shortest-path-count"
    count_paths = True
