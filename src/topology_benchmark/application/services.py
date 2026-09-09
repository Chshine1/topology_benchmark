"""Intent-first benchmark use cases for object and morphism subjects."""

import math
from collections.abc import Callable
from dataclasses import replace
from random import Random

from topology_benchmark.core.models import GenerationRequest, Problem
from topology_benchmark.core.probability import SamplingSession
from topology_benchmark.domains.polyhedral_nets.analysis import PolyhedralNetAnalyzer
from topology_benchmark.domains.polyhedral_nets.generation import RandomPolyhedralNetGenerator
from topology_benchmark.domains.polyhedral_nets.models import (
    EdgePair,
    FaceCorner,
    PolygonFace,
    PolyhedralFolding,
    PolyhedralNet,
)
from topology_benchmark.domains.polyhedral_nets.representation import PolyhedralNetSvgRenderer
from topology_benchmark.domains.surfaces.components.generation_config import (
    SurfaceGenerationConfig,
)
from topology_benchmark.domains.surfaces.components.invariant import (
    morphism_answer,
    object_answer,
)
from topology_benchmark.domains.surfaces.components.question import (
    formulate_morphism,
    formulate_object,
)
from topology_benchmark.domains.surfaces.generation import (
    ProblemSubject,
    SurfaceGenerationContext,
    SurfaceProblemIntent,
)
from topology_benchmark.domains.surfaces.models import SurfacePresentation
from topology_benchmark.domains.surfaces.ports import (
    SurfaceAnswer,
    SurfaceGenerator,
    SurfaceIntentGenerator,
    SurfaceMorphismGenerator,
    SurfaceRepresentation,
)


class SurfaceBenchmark:
    def __init__(
        self,
        generator: SurfaceGenerator,
        morphism_generator: SurfaceMorphismGenerator,
        representation: SurfaceRepresentation,
        intent_generator: SurfaceIntentGenerator,
        generation_config: SurfaceGenerationConfig,
    ) -> None:
        self._generator = generator
        self._morphism_generator = morphism_generator
        self._representation = representation
        self._intent_generator = intent_generator
        self._config = generation_config

    def generate(self, *, seed: int, difficulty: int = 1) -> Problem[SurfaceAnswer]:
        request = GenerationRequest(seed=seed, difficulty=difficulty)
        sampling = SamplingSession(seed, self._config.profile_version)
        intent = self._intent_generator.sample(request, sampling)
        context = SurfaceGenerationContext(request, intent, sampling)
        if intent.subject is ProblemSubject.MORPHISM:
            return self._morphism_problem(context)
        return self._object_problem(context)

    def _object_problem(self, context: SurfaceGenerationContext) -> Problem[SurfaceAnswer]:
        surface = self._generator.generate_for(context)
        prompt = self._representation.render(
            surface,
            context.request,
            context.sampling.rng("render.object"),
        )
        metadata = self._common_metadata(context.intent, context)
        metadata.update(self._surface_metadata(surface))
        return Problem(
            question=formulate_object(surface, context.intent.question_kind, 0),
            prompts=(prompt,),
            answer=object_answer(surface, context.intent.question_kind, 0),
            seed=context.request.seed,
            metadata=metadata,
        )

    def _morphism_problem(self, context: SurfaceGenerationContext) -> Problem[SurfaceAnswer]:
        morphism = self._morphism_generator.generate_for(context)
        prompts = (
            self._representation.render(
                morphism.source,
                context.request,
                context.sampling.rng("render.morphism.source"),
            ),
            self._representation.render(
                morphism.target,
                context.request,
                context.sampling.rng("render.morphism.target"),
            ),
        )
        metadata = self._common_metadata(context.intent, context)
        metadata.update(
            {
                "morphism": morphism.name,
                "morphism_family": morphism.family,
                "identified_edge_pairs": len(morphism.identifications),
                "source_polygons": len(morphism.source.polygons),
                "target_polygons": len(morphism.target.polygons),
            }
        )
        return Problem(
            question=formulate_morphism(context.intent.question_kind),
            prompts=prompts,
            answer=morphism_answer(morphism, context.intent.question_kind),
            seed=context.request.seed,
            metadata=metadata,
        )

    def _common_metadata(
        self,
        intent: SurfaceProblemIntent,
        context: SurfaceGenerationContext,
    ) -> dict[str, str | int | bool]:
        return {
            "difficulty": context.request.difficulty,
            "subject": intent.subject.value,
            "question_focus": intent.focus.value,
            "question_kind": intent.question_kind,
            "generation_profile": self._config.profile_version,
            "intentional_noise": intent.noise
            or any(event.noise for event in context.sampling.events),
            "sampling_trace": context.sampling.trace_json(),
            "visual_parameters_generated": False,
            "renderer_randomness": True,
        }

    @staticmethod
    def _surface_metadata(surface: SurfacePresentation) -> dict[str, int]:
        return {
            "polygon_count": len(surface.polygons),
            "polygon_edges": sum(polygon.sides for polygon in surface.polygons),
            "gluing_count": len(surface.gluings),
            "path_count": len(surface.paths),
            "path_segments": sum(len(path.edges) for path in surface.paths),
        }


type PolyhedralNetAnswer = int | str | bool


class PolyhedralNetsBenchmark:
    """Spatial-inference benchmark over certified observations of real polyhedra."""

    profile_version = "polyhedral-nets-v2"

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
        for attempt in range(30):
            folding = self._generator.generate(request, sampling.rng(f"net.structure.{attempt}"))
            solutions = self._analyzer.enumerate_locally_convex_pairings(folding.net)
            if not solutions:
                continue
            for kind in kinds:
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
                sampling.note("intent.question-kind", kind)
                prompt = self._representation.render(
                    observed, request, sampling.rng("render.object")
                )
                return Problem(
                    question=question,
                    prompts=(prompt,),
                    answer=answer,
                    seed=seed,
                    metadata={
                        "difficulty": difficulty,
                        "domain": "polyhedral-nets",
                        "subject": "object",
                        "question_kind": kind,
                        "generation_profile": self.profile_version,
                        "sampling_trace": sampling.trace_json(),
                        "metric_geometry": True,
                        "source_is_real_3d": True,
                        "drawn_to_scale": True,
                        "partial_gluing_hints": bool(observed.seam_hints),
                    },
                )
        raise RuntimeError("could not generate a certified polyhedral-net question")

    @staticmethod
    def _question_kinds(difficulty: int) -> tuple[str, ...]:
        basic = ("seam-match", "corner-coincidence", "face-relation")
        if difficulty <= 3:
            return basic
        geometric = (*basic, "vertex-degree", "curvature-order")
        if difficulty <= 6:
            return geometric
        advanced = (*geometric, "highest-vertex")
        return (*advanced, "isometric") if difficulty >= 9 else advanced

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
                solutions = self._analyzer.enumerate_locally_convex_pairings(folding.net)
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
                observed.append(replace(folding.net, seam_hints=hints))
            if len(observed) != 2:
                continue
            sampling.note("intent.question-kind", "isometric")
            prompts = tuple(
                self._representation.render(
                    net,
                    request,
                    sampling.rng(f"render.comparison.{index}"),
                )
                for index, net in enumerate(observed)
            )
            return Problem(
                question=(
                    "Do these two to-scale nets reconstruct intrinsically isometric convex "
                    "polyhedral surfaces?"
                ),
                prompts=prompts,
                answer=self._analyzer.isometric(first, second),
                seed=request.seed,
                metadata={
                    "difficulty": request.difficulty,
                    "domain": "polyhedral-nets",
                    "subject": "comparison",
                    "question_kind": "isometric",
                    "generation_profile": self.profile_version,
                    "sampling_trace": sampling.trace_json(),
                    "metric_geometry": True,
                    "source_is_real_3d": True,
                    "drawn_to_scale": True,
                    "partial_gluing_hints": any(net.seam_hints for net in observed),
                },
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

        if kind == "corner-coincidence":
            same = bool(rng.randrange(2))
            first_class = rng.choice(corner_classes)
            corner_first = rng.choice(first_class)
            if same and len(first_class) > 1:
                corner_second = rng.choice(
                    tuple(corner for corner in first_class if corner != corner_first)
                )
            else:
                other = rng.choice(tuple(group for group in corner_classes if group != first_class))
                corner_second = rng.choice(other)

            def answer(seams: tuple[EdgePair, ...]) -> bool:
                return self._same_vertex(net, seams, corner_first, corner_second)

            certified = self._certify(net, truth, solutions, answer, difficulty)
            if certified is None:
                return None
            hints, value = certified
            observed = replace(
                net,
                seam_hints=hints,
                corner_labels=((corner_first, "A"), (corner_second, "B")),
            )
            return (
                "This to-scale net comes from a convex polyhedron. Do marked corners A and B "
                "become the same vertex after folding?",
                value,
                observed,
            )

        if kind == "face-relation":
            hinged = {frozenset((pair.first.face, pair.second.face)) for pair in net.hinges}
            candidates = [
                (first, second)
                for first in range(len(net.faces))
                for second in range(first + 1, len(net.faces))
                if frozenset((first, second)) not in hinged
            ]
            if not candidates:
                return None
            face_first, face_second = rng.choice(candidates)

            def answer(seams: tuple[EdgePair, ...]) -> str:
                return self._face_relation(net, seams, face_first, face_second)

            certified = self._certify(net, truth, solutions, answer, difficulty)
            if certified is None:
                return None
            hints, value = certified
            observed = replace(
                net,
                seam_hints=hints,
                face_labels=((face_first, "A"), (face_second, "B")),
            )
            return (
                "After this convex polyhedron is folded, do faces A and B share an edge, "
                "share only a vertex, or remain disjoint?",
                value,
                observed,
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
                angle_a = next(
                    angle
                    for group, angle in zip(analysis.vertices, analysis.angle_sums, strict=True)
                    if curvature_first in group
                )
                angle_b = next(
                    angle
                    for group, angle in zip(analysis.vertices, analysis.angle_sums, strict=True)
                    if curvature_second in group
                )
                difference = float(angle_a) - float(angle_b)
                return "A" if difference < -1e-8 else "B" if difference > 1e-8 else "equal"

            certified = self._certify(net, truth, solutions, answer, difficulty)
            if certified is None:
                return None
            hints, value = certified
            observed = replace(
                net,
                seam_hints=hints,
                corner_labels=((curvature_first, "A"), (curvature_second, "B")),
            )
            return (
                "Which folded vertex has greater angular defect (discrete curvature): A, B, "
                "or are they equal?",
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

        if kind == "highest-vertex":
            return self._highest_vertex_question(folding, solutions, difficulty, rng)
        return None

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
        budget = 0 if difficulty <= 3 else 1 if difficulty <= 6 else 3
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

    def _highest_vertex_question(
        self,
        folding: PolyhedralFolding,
        solutions: tuple[tuple[EdgePair, ...], ...],
        difficulty: int,
        rng: Random,
    ) -> tuple[str, PolyhedralNetAnswer, PolyhedralNet] | None:
        source = folding.source
        if source is None:
            return None
        unique = self._certify(
            folding.net,
            folding.seams,
            solutions,
            lambda seams: True,
            difficulty,
            require_unique=True,
        )
        if unique is None:
            return None
        hints, _ = unique
        root = source.faces[folding.root_face]
        a, b, c = (source.vertices[root[index]] for index in range(3))
        ab = tuple(float(y - x) for x, y in zip(a, b, strict=True))
        ac = tuple(float(y - x) for x, y in zip(a, c, strict=True))
        normal = (
            ab[1] * ac[2] - ab[2] * ac[1],
            ab[2] * ac[0] - ab[0] * ac[2],
            ab[0] * ac[1] - ab[1] * ac[0],
        )
        norm = math.sqrt(sum(value * value for value in normal))
        heights = {
            vertex: -sum(float(point[index] - a[index]) * normal[index] for index in range(3))
            / norm
            for vertex, point in enumerate(source.vertices)
        }
        ordered = sorted((height, vertex) for vertex, height in heights.items())
        if len(ordered) < 2 or ordered[-1][0] - ordered[0][0] < 1e-8:
            return None
        selected = [ordered[0][1], ordered[-1][1]]
        middle = [vertex for _, vertex in ordered[1:-1]]
        if middle:
            selected.append(rng.choice(middle))
        corner_by_source: dict[int, FaceCorner] = {}
        for face_index, face in enumerate(folding.net.faces):
            if isinstance(face, PolygonFace):
                for corner, source_vertex in enumerate(face.source_vertices):
                    corner_by_source.setdefault(source_vertex, FaceCorner(face_index, corner))
        labels = tuple(
            (corner_by_source[vertex], chr(65 + index)) for index, vertex in enumerate(selected)
        )
        answer = max(range(len(selected)), key=lambda index: heights[selected[index]])
        observed = replace(
            folding.net,
            seam_hints=hints,
            corner_labels=labels,
            face_labels=((folding.root_face, "BASE"),),
        )
        return (
            "Place face BASE on a horizontal table and fold the convex polyhedron above it. "
            "Which marked vertex is highest?",
            chr(65 + answer),
            observed,
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

    def _face_relation(
        self, net: PolyhedralNet, seams: tuple[EdgePair, ...], first: int, second: int
    ) -> str:
        if any(
            {pair.first.face, pair.second.face} == {first, second} for pair in (*net.hinges, *seams)
        ):
            return "edge"
        analysis = self._analyzer.analyze(net, seams)
        if any(
            {corner.face for corner in vertex}.issuperset((first, second))
            for vertex in analysis.vertices
        ):
            return "vertex"
        return "disjoint"


PolyhedralNetBenchmark = PolyhedralNetsBenchmark
