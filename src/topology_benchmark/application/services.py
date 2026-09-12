from collections import deque
from collections.abc import Callable
from dataclasses import replace
from random import Random

from topology_benchmark.core.models import GenerationRequest, Problem
from topology_benchmark.core.probability import SamplingSession
from topology_benchmark.core.protocols import ProblemProvider
from topology_benchmark.domains.polyhedral_nets.analysis import PolyhedralNetAnalyzer
from topology_benchmark.domains.polyhedral_nets.generation import RandomPolyhedralNetGenerator
from topology_benchmark.domains.polyhedral_nets.models import (
    EdgePair,
    FaceCorner,
    NetEdge,
    PolyhedralFolding,
    PolyhedralNet,
)
from topology_benchmark.domains.polyhedral_nets.representation import PolyhedralNetSvgRenderer
from topology_benchmark.domains.surfaces.analysis import SurfaceAnalyzer
from topology_benchmark.domains.surfaces.components.generation_config import (
    SurfaceGenerationConfig,
)
from topology_benchmark.domains.surfaces.components.invariant import object_answer
from topology_benchmark.domains.surfaces.components.question import formulate_object
from topology_benchmark.domains.surfaces.generation import (
    SurfaceGenerationContext,
)
from topology_benchmark.domains.surfaces.ports import (
    SurfaceAnswer,
    SurfaceGenerator,
    SurfaceIntentGenerator,
    SurfaceRepresentation,
)


class SurfaceBenchmark(ProblemProvider):
    def __init__(
        self,
        generator: SurfaceGenerator,
        representation: SurfaceRepresentation,
        intent_generator: SurfaceIntentGenerator,
        generation_config: SurfaceGenerationConfig,
        analyzer: SurfaceAnalyzer,
    ) -> None:
        self._generator = generator
        self._representation = representation
        self._intent_generator = intent_generator
        self._config = generation_config
        self._analyzer = analyzer

    def generate(self, *, seed: int, difficulty: int = 1) -> Problem[SurfaceAnswer]:
        request = GenerationRequest(seed=seed, difficulty=difficulty)
        sampling = SamplingSession(seed, self._config.profile_version)
        intent = self._intent_generator.sample(request, sampling)
        context = SurfaceGenerationContext(request, intent, sampling)
        return self._object_problem(context)

    def _object_problem(self, context: SurfaceGenerationContext) -> Problem[SurfaceAnswer]:
        surface = self._generator.generate_for(context)
        edge_labels = ()
        if context.intent.question_kind == "path-representative":
            used_edges = {
                edge
                for coefficients, _ in self._analyzer.h1_edge_generators(surface)
                for edge, coefficient in enumerate(coefficients)
                if coefficient
            }
            homology = self._analyzer.cellular_homology(surface)
            edge_labels = tuple(
                (homology.edge_basis[edge], f"e{tag}")
                for tag, edge in enumerate(sorted(used_edges), start=1)
            )
        section = self._representation.render(
            surface,
            context.request,
            context.sampling.rng("render.object"),
            edge_labels=edge_labels,
        )
        return Problem(
            question=formulate_object(self._analyzer, surface, context.intent.question_kind, 0),
            sections=(section,),
            answer=object_answer(self._analyzer, surface, context.intent.question_kind, 0),
            seed=context.request.seed,
            question_kind=context.intent.question_kind,
        )


type PolyhedralNetAnswer = int | str | bool
type MarkedNetCell = tuple[str, int, int]


class PolyhedralNetsBenchmark(ProblemProvider):
    profile_version = "polyhedral-nets-v6"
    # Below this relative difference, a rendered edge-length distinction is not treated as
    # observable. This prevents hidden exact metrics from silently resolving a seam ambiguity.
    visual_length_tolerance = 0.04

    def __init__(
        self,
        generator: RandomPolyhedralNetGenerator,
        analyzer: PolyhedralNetAnalyzer,
        representation: PolyhedralNetSvgRenderer,
    ) -> None:
        self._generator = generator
        self._analyzer = analyzer
        self._representation = representation

    def generate(self, *, seed: int, difficulty: int = 1) -> Problem[PolyhedralNetAnswer]:
        request = GenerationRequest(seed=seed, difficulty=difficulty)
        sampling = SamplingSession(seed, self.profile_version)
        kinds = list(self._question_kinds(difficulty))
        rng = sampling.rng("intent.question-kind")
        rng.shuffle(kinds)
        if kinds[0] == "isometric":
            comparison = self._isometry_problem(request, sampling)
            if comparison is not None:
                return comparison
            kinds.remove("isometric")
        for kind in kinds:
            for attempt in range(30):
                folding = self._generator.generate(
                    request, sampling.rng(f"net.structure.{kind}.{attempt}")
                )
                solutions = self._observable_pairings(folding.net)
                if not solutions:
                    continue
                built = self._build_question(
                    folding,
                    solutions,
                    kind,
                    difficulty,
                    sampling.rng(f"question.{attempt}.{kind}"),
                )
                if built is None:
                    continue
                question, answer, observed = built
                section = self._representation.render(
                    observed, request, sampling.rng("render.object")
                )
                return Problem(
                    question=question,
                    sections=(section,),
                    answer=answer,
                    seed=seed,
                    question_kind=kind,
                )
        raise RuntimeError("could not generate a certified polyhedral-net question")

    @staticmethod
    def _question_kinds(difficulty: int) -> tuple[str, ...]:
        basic = ("seam-match", "vertex-partition", "cell-distance")
        if difficulty <= 3:
            return basic
        geometric = (*basic, "vertex-degree", "curvature-order", "cell-shortest-path-count")
        if difficulty <= 6:
            return geometric
        # A sound non-isometry needs different convex assemblies of the same visible panel kit;
        # different face inventories would reveal the answer without spatial reasoning.
        return geometric

    def _isometry_problem(
        self, request: GenerationRequest, sampling: SamplingSession
    ) -> Problem[PolyhedralNetAnswer] | None:
        expected = sampling.rng("isometry.truth").random() < 0.5
        for attempt in range(20):
            first, second = self._generator.generate_isometry_pair(
                request,
                sampling.rng(f"isometry.structure.{attempt}"),
                isometric=expected,
            )
            observed: list[PolyhedralNet] = []
            for folding in (first, second):
                solutions = self._observable_pairings(folding.net)
                certificate = self._certify(
                    folding.net,
                    folding.seams,
                    solutions,
                    lambda seams: True,
                    request.difficulty,
                    require_unique=True,
                )
                if certificate is None:
                    break
                hints, _ = certificate
                face_labels = tuple(
                    (face, f"F{face + 1}") for face in range(len(folding.net.faces))
                )
                observed.append(replace(folding.net, seam_hints=hints, face_labels=face_labels))
            if len(observed) != 2:
                continue
            common_scale = self._representation.common_scale(tuple(observed))
            sections = tuple(
                self._representation.render(
                    net,
                    request,
                    sampling.rng(f"render.comparison.{index}"),
                    scale=common_scale,
                )
                for index, net in enumerate(observed)
            )
            return Problem(
                question=(
                    "The diagrams use a common scale, and equally labelled faces are proposed "
                    "correspondences. Do the nets reconstruct intrinsically isometric convex "
                    "polyhedral surfaces?"
                ),
                sections=sections,
                answer=self._analyzer.isometric(first, second),
                seed=request.seed,
                question_kind="isometric",
            )
        return None

    def _build_question(
        self,
        folding: PolyhedralFolding,
        solutions: tuple[tuple[EdgePair, ...], ...],
        kind: str,
        difficulty: int,
        rng: Random,
    ) -> tuple[str, PolyhedralNetAnswer, PolyhedralNet] | None:
        net = folding.net
        truth = folding.seams
        truth_analysis = self._analyzer.analyze(folding)
        corner_classes = list(truth_analysis.vertices)

        if kind == "vertex-partition":
            return self._vertex_partition_question(
                folding, solutions, difficulty, rng, corner_classes
            )

        if kind in ("cell-distance", "cell-shortest-path-count"):
            return self._cell_distance_question(
                folding,
                solutions,
                difficulty,
                rng,
                count_paths=kind == "cell-shortest-path-count",
            )

        if kind == "vertex-degree":
            corner = rng.choice(rng.choice(corner_classes))

            def answer(seams: tuple[EdgePair, ...]) -> int:
                analysis = self._analyzer.analyze(net, seams)
                vertex = next(group for group in analysis.vertices if corner in group)
                return len({item.face for item in vertex})

            certified = self._certify(net, truth, solutions, answer, difficulty)
            if certified is None:
                return None
            hints, value = certified
            observed = replace(net, seam_hints=hints, corner_labels=((corner, "A"),))
            return (
                "How many faces meet at the folded vertex containing marked corner A?",
                value,
                observed,
            )

        if kind == "curvature-order":
            first_class, second_class = rng.sample(corner_classes, 2)
            curvature_first = rng.choice(first_class)
            curvature_second = rng.choice(second_class)

            def answer(seams: tuple[EdgePair, ...]) -> str:
                analysis = self._analyzer.analyze(net, seams)
                group_a = next(group for group in analysis.vertices if curvature_first in group)
                group_b = next(group for group in analysis.vertices if curvature_second in group)
                angle_a = sum(round(float(net.corner_angle_degrees(corner))) for corner in group_a)
                angle_b = sum(round(float(net.corner_angle_degrees(corner))) for corner in group_b)
                difference = angle_a - angle_b
                return "A" if difference < -1e-8 else "B" if difference > 1e-8 else "equal"

            exact_a = sum(net.corner_angle_degrees(corner) for corner in first_class)
            exact_b = sum(net.corner_angle_degrees(corner) for corner in second_class)
            visible_a = sum(
                round(float(net.corner_angle_degrees(corner))) for corner in first_class
            )
            visible_b = sum(
                round(float(net.corner_angle_degrees(corner))) for corner in second_class
            )
            exact_difference = float(exact_a) - float(exact_b)
            visible_difference = visible_a - visible_b
            if (
                abs(exact_difference) < 8.0
                or abs(visible_difference) < 6
                or exact_difference * visible_difference <= 0
            ):
                return None

            certified = self._certify(net, truth, solutions, answer, difficulty)
            if certified is None:
                return None
            hints, value = certified
            displayed_angles = tuple(
                (
                    FaceCorner(face_index, corner),
                    f"{round(float(net.corner_angle_degrees(FaceCorner(face_index, corner))))}°",
                )
                for face_index, face in enumerate(net.faces)
                for corner in range(face.sides)
            )
            observed = replace(
                net,
                seam_hints=hints,
                corner_labels=((curvature_first, "A"), (curvature_second, "B")),
                corner_angle_labels=displayed_angles,
            )
            return (
                "Corner angles are shown to the nearest degree. Which folded vertex has "
                "greater angular defect (discrete curvature): A or B?",
                value,
                observed,
            )

        if kind == "seam-match":
            target_pair = rng.choice(truth)
            target = target_pair.first
            mate = target_pair.second
            distractors = [edge for edge in net.boundary_edges if edge not in (target, mate)]
            rng.shuffle(distractors)
            same_length = [
                edge for edge in distractors if net.edge_metric(edge) == net.edge_metric(target)
            ]
            others = [edge for edge in distractors if edge not in same_length]
            candidates = [mate, *same_length[:2]]
            candidates.extend(others[: 3 - len(candidates)])
            rng.shuffle(candidates)
            labels = (
                (target, "A"),
                *((edge, chr(66 + index)) for index, edge in enumerate(candidates)),
            )

            def answer(seams: tuple[EdgePair, ...]) -> str:
                pair = next((pair for pair in seams if target in pair.unordered), None)
                if pair is None:
                    return "none"
                partner = next(edge for edge in pair.unordered if edge != target)
                return dict((edge, label) for edge, label in labels).get(partner, "none")

            certified = self._certify(
                net,
                truth,
                solutions,
                answer,
                difficulty,
                forbidden_hints=(target_pair,),
            )
            if certified is None:
                return None
            hints, value = certified
            observed = replace(net, seam_hints=hints, edge_labels=tuple(labels))
            return (
                "When the convex polyhedron is reconstructed, which labelled boundary edge "
                "is glued to edge A?",
                value,
                observed,
            )

        return None

    def _vertex_partition_question(
        self,
        folding: PolyhedralFolding,
        solutions: tuple[tuple[EdgePair, ...], ...],
        difficulty: int,
        rng: Random,
        corner_classes: list[tuple[FaceCorner, ...]],
    ) -> tuple[str, PolyhedralNetAnswer, PolyhedralNet] | None:
        repeated = [group for group in corner_classes if len(group) >= 2]
        if not repeated or len(corner_classes) < 2:
            return None
        count = 4 if difficulty <= 5 else 5
        first_group = rng.choice(repeated)
        second_group = rng.choice([group for group in corner_classes if group != first_group])
        selected = [*rng.sample(first_group, 2), rng.choice(second_group)]
        remaining = [
            corner for group in corner_classes for corner in group if corner not in selected
        ]
        rng.shuffle(remaining)
        selected.extend(remaining[: count - len(selected)])
        if len(selected) != count:
            return None
        rng.shuffle(selected)
        labels = tuple((corner, chr(ord("A") + index)) for index, corner in enumerate(selected))

        def answer(seams: tuple[EdgePair, ...]) -> str:
            analysis = self._analyzer.analyze(folding.net, seams)
            groups = [
                "".join(sorted(label for corner, label in labels if corner in vertex))
                for vertex in analysis.vertices
            ]
            return "|".join(sorted(group for group in groups if group))

        certified = self._certify(folding.net, folding.seams, solutions, answer, difficulty)
        if certified is None:
            return None
        hints, value = certified
        observed = replace(folding.net, seam_hints=hints, corner_labels=labels)
        return (
            "Partition marked corners A through "
            f"{chr(ord('A') + count - 1)} by the folded vertex they become. Write letters in "
            "each group alphabetically and separate the groups with |, for example AC|B|D.",
            value,
            observed,
        )

    def _cell_distance_question(
        self,
        folding: PolyhedralFolding,
        solutions: tuple[tuple[EdgePair, ...], ...],
        difficulty: int,
        rng: Random,
        *,
        count_paths: bool,
    ) -> tuple[str, PolyhedralNetAnswer, PolyhedralNet] | None:
        analysis = self._analyzer.analyze(folding)
        kinds = ("face",) if difficulty <= 3 else ("face", "edge")
        if difficulty >= 7:
            kinds = ("face", "edge", "vertex")
        cells: list[MarkedNetCell] = []
        if "face" in kinds:
            cells.extend(("face", face, -1) for face in range(len(folding.net.faces)))
        if "edge" in kinds:
            cells.extend(("edge", edge.face, edge.edge) for edge in folding.net.boundary_edges)
        if "vertex" in kinds:
            cells.extend(
                ("vertex", representative.face, representative.corner)
                for vertex in analysis.vertices
                for representative in (rng.choice(vertex),)
            )
        candidates = [
            (first, second)
            for first_index, first in enumerate(cells)
            for second in cells[first_index + 1 :]
            if first != second
        ]
        rng.shuffle(candidates)
        prefer_zero = bool(rng.randrange(2))
        preferred = [
            pair
            for pair in candidates
            if (self._cell_distance_statistics(folding.net, folding.seams, *pair)[0] == 0)
            == prefer_zero
        ]
        if preferred:
            candidates = preferred
        for first, second in candidates[:24]:

            def answer(
                seams: tuple[EdgePair, ...],
                first_cell: MarkedNetCell = first,
                second_cell: MarkedNetCell = second,
            ) -> int:
                distance, path_count = self._cell_distance_statistics(
                    folding.net, seams, first_cell, second_cell
                )
                return path_count if count_paths else distance

            certified = self._certify(folding.net, folding.seams, solutions, answer, difficulty)
            if certified is None:
                continue
            hints, value = certified
            observed = self._mark_cells(folding.net, hints, first, second)
            first_name = self._cell_name(first, "A")
            second_name = self._cell_name(second, "B")
            if count_paths:
                question = (
                    f"How many shortest vertex paths in the folded 1-skeleton connect {first_name} "
                    f"to {second_name}? Path length is the number of edges. Distinct paths have "
                    "different vertex sequences; each common vertex gives one zero-edge path."
                )
            else:
                question = (
                    f"What is the minimum number of edges in a vertex path through the folded "
                    f"1-skeleton connecting {first_name} to {second_name}?"
                )
            return question, value, observed
        return None

    def _cell_distance_statistics(
        self,
        net: PolyhedralNet,
        seams: tuple[EdgePair, ...],
        first: MarkedNetCell,
        second: MarkedNetCell,
    ) -> tuple[int, int]:
        analysis = self._analyzer.analyze(net, seams)
        vertex_of = {
            corner: vertex for vertex, corners in enumerate(analysis.vertices) for corner in corners
        }
        adjacency = [set() for _ in analysis.vertices]
        for face_index, face in enumerate(net.faces):
            for edge in range(face.sides):
                start = vertex_of[FaceCorner(face_index, edge)]
                end = vertex_of[FaceCorner(face_index, (edge + 1) % face.sides)]
                if start != end:
                    adjacency[start].add(end)
                    adjacency[end].add(start)

        def vertices(cell: MarkedNetCell) -> set[int]:
            kind, face, item = cell
            if kind == "vertex":
                return {vertex_of[FaceCorner(face, item)]}
            if kind == "edge":
                return {
                    vertex_of[FaceCorner(face, item)],
                    vertex_of[FaceCorner(face, (item + 1) % net.faces[face].sides)],
                }
            return {vertex_of[FaceCorner(face, corner)] for corner in range(net.faces[face].sides)}

        sources, targets = vertices(first), vertices(second)
        common = sources & targets
        if common:
            return 0, len(common)
        distances = {vertex: 0 for vertex in sources}
        ways = dict.fromkeys(sources, 1)
        pending = deque(sources)
        while pending:
            current = pending.popleft()
            for neighbor in adjacency[current]:
                candidate = distances[current] + 1
                if neighbor not in distances:
                    distances[neighbor] = candidate
                    ways[neighbor] = ways[current]
                    pending.append(neighbor)
                elif distances[neighbor] == candidate:
                    ways[neighbor] += ways[current]
        distance = min(distances[target] for target in targets)
        return distance, sum(ways[target] for target in targets if distances[target] == distance)

    @staticmethod
    def _mark_cells(
        net: PolyhedralNet,
        hints: tuple[EdgePair, ...],
        first: MarkedNetCell,
        second: MarkedNetCell,
    ) -> PolyhedralNet:
        corners = []
        edges = []
        faces = []
        for cell, label in ((first, "A"), (second, "B")):
            kind, face, item = cell
            if kind == "vertex":
                corners.append((FaceCorner(face, item), label))
            elif kind == "edge":
                edges.append((NetEdge(face, item), label))
            else:
                faces.append((face, label))
        return replace(
            net,
            seam_hints=hints,
            corner_labels=tuple(corners),
            edge_labels=tuple(edges),
            face_labels=tuple(faces),
        )

    @staticmethod
    def _cell_name(cell: MarkedNetCell, label: str) -> str:
        return {
            "vertex": f"the folded vertex containing corner {label}",
            "edge": f"the folded edge containing boundary edge {label}",
            "face": f"face {label}",
        }[cell[0]]

    def _certify(
        self,
        net: PolyhedralNet,
        truth: tuple[EdgePair, ...],
        solutions: tuple[tuple[EdgePair, ...], ...],
        answer: Callable[[tuple[EdgePair, ...]], PolyhedralNetAnswer],
        difficulty: int,
        *,
        require_unique: bool = False,
        forbidden_hints: tuple[EdgePair, ...] = (),
    ) -> tuple[tuple[EdgePair, ...], PolyhedralNetAnswer] | None:
        compute = answer
        candidates = list(solutions)
        hints: list[EdgePair] = []
        # Reduce hints with difficulty, but reject instances whose answer remains ambiguous.
        budget = 3 if difficulty <= 3 else 2 if difficulty <= 6 else 1
        target = compute(truth)
        while (
            len(candidates) != 1
            if require_unique
            else {compute(item) for item in candidates} != {target}
        ):
            if len(hints) >= budget:
                return None
            forbidden = {pair.unordered for pair in forbidden_hints}
            options = [
                pair for pair in truth if pair not in hints and pair.unordered not in forbidden
            ]
            scored = []
            for hint in options:
                remaining = [
                    solution for solution in candidates if self._contains_pair(solution, hint)
                ]
                if remaining:
                    score = (len({compute(item) for item in remaining}), len(remaining))
                    scored.append((score, hint, remaining))
            if not scored:
                return None
            _, chosen, candidates = min(scored, key=lambda item: item[0])
            hints.append(chosen)
        return tuple(hints), target

    def _observable_pairings(self, net: PolyhedralNet) -> tuple[tuple[EdgePair, ...], ...]:
        return self._analyzer.enumerate_locally_convex_pairings(
            net,
            relative_length_tolerance=self.visual_length_tolerance,
        )

    @staticmethod
    def _contains_pair(solution: tuple[EdgePair, ...], target: EdgePair) -> bool:
        return any(pair.unordered == target.unordered for pair in solution)

    def _same_vertex(
        self,
        net: PolyhedralNet,
        seams: tuple[EdgePair, ...],
        first: FaceCorner,
        second: FaceCorner,
    ) -> bool:
        return any(
            first in group and second in group
            for group in self._analyzer.analyze(net, seams).vertices
        )
