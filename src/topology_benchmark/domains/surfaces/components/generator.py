"""Intent-aware probabilistic generators of polygon-edge presentations."""

import math
from random import Random

from topology_benchmark.core.models import GenerationRequest
from topology_benchmark.core.probability import (
    BernoulliDistribution,
    FiniteDistribution,
    SamplingSession,
    TruncatedGeometricDistribution,
    WeightedValue,
    blended_weight,
)
from topology_benchmark.domains.surfaces.analysis import SurfaceAnalyzer
from topology_benchmark.domains.surfaces.components.generation_config import (
    SurfaceGenerationConfig,
    load_generation_config,
)
from topology_benchmark.domains.surfaces.generation import (
    ProblemSubject,
    QuestionFocus,
    SurfaceGenerationContext,
    SurfaceProblemIntent,
)
from topology_benchmark.domains.surfaces.models import (
    BoundaryGluingMorphism,
    EdgeGluing,
    EdgeRef,
    OrientedEdge,
    Polygon,
    PolygonAttachmentMorphism,
    SurfaceMorphism,
    SurfacePath,
    SurfacePresentation,
)
from topology_benchmark.domains.surfaces.ports import SurfaceGenerator, SurfaceMorphismGenerator


class RandomSurfacePresentationGenerator(SurfaceGenerator):
    """Sample a valid surface using soft weights conditioned on problem intent."""

    def __init__(self, config: SurfaceGenerationConfig | None = None) -> None:
        self.config = config or load_generation_config()

    def generate(self, request: GenerationRequest, rng: Random) -> SurfacePresentation:
        sampling = SamplingSession(request.seed, self.config.profile_version)
        intent = SurfaceProblemIntent(
            ProblemSubject.OBJECT, "euler-characteristic", QuestionFocus.GLOBAL
        )
        return self._generate(SurfaceGenerationContext(request, intent, sampling), rng)

    def generate_for(self, context: SurfaceGenerationContext) -> SurfacePresentation:
        return self._generate(context, context.sampling.rng("surface.structure"))

    def _generate(self, context: SurfaceGenerationContext, rng: Random) -> SurfacePresentation:
        for _ in range(self.config.retry_limit):
            polygon_count = self._polygon_count(context, rng)
            polygons = tuple(
                Polygon(chr(ord("P") + index), self._side_count(context.request, rng))
                for index in range(polygon_count)
            )
            edges = [
                EdgeRef(polygon, edge)
                for polygon, shape in enumerate(polygons)
                for edge in range(shape.sides)
            ]
            pair_count = self._pair_count(context, len(edges), rng)
            rng.shuffle(edges)
            selected = edges[: 2 * pair_count]
            gluings = tuple(
                EdgeGluing(
                    selected[2 * index],
                    selected[2 * index + 1],
                    self._label(index),
                    rng.choice((True, False)),
                )
                for index in range(pair_count)
            )
            candidate = SurfacePresentation(polygons, gluings)
            try:
                SurfaceAnalyzer().analyze(candidate)
            except ValueError:
                continue
            paths = self._paths(candidate, context)
            context.sampling.note("surface.relaxed", False)
            return SurfacePresentation(polygons, gluings, paths)

        context.sampling.note("surface.relaxed", True, noise=True)
        sides = 3 + context.sampling.rng("surface.fallback").randrange(4)
        fallback = SurfacePresentation((Polygon("P", sides),), ())
        return SurfacePresentation(fallback.polygons, (), self._paths(fallback, context))

    def _polygon_count(self, context: SurfaceGenerationContext, rng: Random) -> int:
        profile = self.config.difficulty
        difficulty = context.request.difficulty
        target = profile.visual_budget.at(difficulty)
        options = []
        for count, weights in profile.polygon_count_weights.items():
            aligned = weights.at(difficulty)
            if context.intent.question_kind == "connected-components":
                aligned *= 3.0 if count >= 2 else 0.35
            if context.intent.focus is QuestionFocus.PATH and count > 2:
                aligned *= 0.3
            aligned *= math.exp(-0.35 * max(0.0, count - target / 2) ** 2)
            options.append(
                WeightedValue(
                    count,
                    blended_weight(aligned, 0.25, self.config.noise_probability),
                )
            )
        return FiniteDistribution(tuple(options)).sample(rng)

    def _side_count(self, request: GenerationRequest, rng: Random) -> int:
        continuation = self.config.difficulty.side_continuation.at(request.difficulty)
        return TruncatedGeometricDistribution(3, 8, continuation).sample(rng)

    def _pair_count(self, context: SurfaceGenerationContext, edge_count: int, rng: Random) -> int:
        maximum = edge_count // 2
        density = self.config.difficulty.gluing_density.at(context.request.difficulty)
        if context.intent.focus is QuestionFocus.CLASSIFICATION:
            density = min(0.85, density * 1.2)
        target = density * maximum
        budget = self.config.difficulty.visual_budget.at(context.request.difficulty)
        options = tuple(
            WeightedValue(
                count,
                blended_weight(
                    math.exp(-0.55 * (count - target) ** 2)
                    * math.exp(-0.5 * max(0.0, count - budget) ** 2),
                    1 / (maximum + 1),
                    self.config.noise_probability,
                ),
            )
            for count in range(maximum + 1)
        )
        return FiniteDistribution(options).sample(rng)

    def _paths(
        self, surface: SurfacePresentation, context: SurfaceGenerationContext
    ) -> tuple[SurfacePath, ...]:
        focused = context.intent.focus is QuestionFocus.PATH
        incidental: bool = False
        if not focused:
            incidental = context.sampling.sample(
                "paths.incidental",
                BernoulliDistribution(self.config.noise_probability),
                noise=True,
            )
        extra: bool = False
        if focused:
            extra = context.sampling.sample(
                "paths.extra",
                BernoulliDistribution(self.config.noise_probability),
                noise=True,
            )
        count = int(focused or incidental) + int(extra)
        paths: list[SurfacePath] = []
        remaining_segments = 7
        for index in range(count):
            reserved_for_later = count - index - 1
            maximum = remaining_segments - reserved_for_later
            path = self._path(surface, context, index, maximum)
            paths.append(path)
            remaining_segments -= len(path.edges)
        return tuple(paths)

    def _path(
        self,
        surface: SurfacePresentation,
        context: SurfaceGenerationContext,
        index: int,
        segment_budget: int,
    ) -> SurfacePath:
        maximum = min(
            segment_budget,
            max(1, round(self.config.difficulty.path_maximum.at(context.request.difficulty))),
        )
        continuation = self.config.difficulty.path_continuation.at(context.request.difficulty)
        length = context.sampling.sample(
            f"path.{index}.length",
            TruncatedGeometricDistribution(1, maximum, continuation),
        )
        must_be_closed: bool = context.intent.question_kind == "path-representative" and index == 0
        if context.intent.question_kind == "path-is-cycle" and index == 0:
            must_be_closed = context.sampling.sample(
                f"path.{index}.closed", BernoulliDistribution(0.55)
            )
        elif not must_be_closed:
            must_be_closed = context.sampling.sample(
                f"path.{index}.closed", BernoulliDistribution(0.5)
            )
        rng = context.sampling.rng(f"path.{index}.walk")
        quotient = surface._quotient_vertices()
        directed = tuple(
            OrientedEdge(EdgeRef(polygon, edge), forward)
            for polygon, shape in enumerate(surface.polygons)
            for edge in range(shape.sides)
            for forward in (True, False)
        )
        outgoing: dict[int, list[OrientedEdge]] = {}
        for edge in directed:
            start = surface._path_endpoint(edge, True, quotient)
            outgoing.setdefault(start, []).append(edge)
        for _ in range(80):
            walk = [rng.choice(directed)]
            for _ in range(length - 1):
                current = surface._path_endpoint(walk[-1], False, quotient)
                choices = outgoing[current]
                weighted = tuple(
                    WeightedValue(
                        choice,
                        0.15
                        if choice.edge == walk[-1].edge and choice.forward != walk[-1].forward
                        else 1.0,
                    )
                    for choice in choices
                )
                walk.append(FiniteDistribution(weighted).sample(rng))
            closed = surface._path_endpoint(walk[0], True, quotient) == surface._path_endpoint(
                walk[-1], False, quotient
            )
            if closed == must_be_closed:
                return SurfacePath(chr(ord("p") + index), tuple(walk))

        if must_be_closed and maximum >= 2:
            edge = rng.choice(directed)
            walk = (edge, OrientedEdge(edge.edge, not edge.forward))
        else:
            edge = next(
                (
                    item
                    for item in directed
                    if surface._path_endpoint(item, True, quotient)
                    != surface._path_endpoint(item, False, quotient)
                ),
                directed[0],
            )
            walk = (edge,)
        return SurfacePath(chr(ord("p") + index), walk)

    @staticmethod
    def _label(index: int) -> str:
        alphabet = "abcdefghijklmnopqrstuvwxyz"
        return alphabet[index] if index < len(alphabet) else f"g{index + 1}"


class RandomSurfaceMorphismGenerator(SurfaceMorphismGenerator):
    """Sample varied instances of the two supported mathematical arrow types."""

    def __init__(self, config: SurfaceGenerationConfig | None = None) -> None:
        self.config = config or load_generation_config()

    def generate(self, request: GenerationRequest, rng: Random) -> SurfaceMorphism:
        sampling = SamplingSession(request.seed, self.config.profile_version)
        intent = SurfaceProblemIntent(
            ProblemSubject.MORPHISM, "boundary-change", QuestionFocus.RELATIONAL
        )
        return self._generate(SurfaceGenerationContext(request, intent, sampling), rng)

    def generate_for(self, context: SurfaceGenerationContext) -> SurfaceMorphism:
        return self._generate(context, context.sampling.rng("morphism.structure"))

    def _generate(self, context: SurfaceGenerationContext, rng: Random) -> SurfaceMorphism:
        family = self._family(context)
        for _ in range(40):
            try:
                if family == "full-disk-boundary":
                    sides = self._side_count(context.request, rng)
                    return self._glue_two_disks(rng, sides)
                if family == "attachment":
                    return self._attach_polygon(rng)
                if family == "partial-intercomponent":
                    return self._partial_intercomponent(rng, context.request.difficulty)
                if family == "self-boundary":
                    return self._self_boundary(rng, context.request.difficulty)
                return self._close_annulus(rng)
            except ValueError:
                continue
        context.sampling.note("morphism.relaxed", True, noise=True)
        return self._attach_polygon(rng)

    def _family(self, context: SurfaceGenerationContext) -> str:
        affinity = self.config.morphism_affinity.get(context.intent.question_kind, {})
        options = tuple(
            WeightedValue(
                family,
                blended_weight(
                    weights.at(context.request.difficulty) * affinity.get(family, 1.0),
                    weights.at(context.request.difficulty),
                    self.config.noise_probability,
                ),
            )
            for family, weights in self.config.morphism_family_weights.items()
        )
        return context.sampling.sample("morphism.family", FiniteDistribution(options))

    def _side_count(self, request: GenerationRequest, rng: Random) -> int:
        continuation = self.config.difficulty.side_continuation.at(request.difficulty)
        return TruncatedGeometricDistribution(3, 8, continuation).sample(rng)

    @staticmethod
    def _attach_polygon(rng: Random) -> PolygonAttachmentMorphism:
        source_sides, attached_sides = rng.randint(3, 6), rng.randint(3, 6)
        source = SurfacePresentation((Polygon("D", source_sides),), ())
        attachment = EdgeGluing(EdgeRef(0, 1), EdgeRef(1, 0), "a", False)
        target = SurfacePresentation(
            (Polygon("D", source_sides), Polygon("A", attached_sides)), (attachment,)
        )
        SurfaceAnalyzer().analyze(target)
        return PolygonAttachmentMorphism(source, target, attachment, 1, "attachment")

    @staticmethod
    def _glue_two_disks(rng: Random, sides: int) -> BoundaryGluingMorphism:
        del rng
        polygons = (Polygon("D1", sides), Polygon("D2", sides))
        source = SurfacePresentation(polygons, ())
        identifications = tuple(
            EdgeGluing(EdgeRef(0, edge), EdgeRef(1, sides - 1 - edge), f"g{edge + 1}", False)
            for edge in range(sides)
        )
        return RandomSurfaceMorphismGenerator._build(source, identifications, "full-disk-boundary")

    @staticmethod
    def _partial_intercomponent(rng: Random, difficulty: int) -> BoundaryGluingMorphism:
        first_sides, second_sides = rng.randint(3, 7), rng.randint(3, 7)
        source = SurfacePresentation((Polygon("D1", first_sides), Polygon("D2", second_sides)), ())
        maximum = min(first_sides, second_sides) - 1
        count = rng.randint(1, min(maximum, 1 + difficulty // 3))
        identifications = tuple(
            EdgeGluing(EdgeRef(0, edge), EdgeRef(1, count - 1 - edge), f"g{edge + 1}", False)
            for edge in range(count)
        )
        return RandomSurfaceMorphismGenerator._build(
            source, identifications, "partial-intercomponent"
        )

    @staticmethod
    def _self_boundary(rng: Random, difficulty: int) -> BoundaryGluingMorphism:
        sides = rng.randint(4, min(8, 4 + difficulty // 2))
        source = SurfacePresentation((Polygon("D", sides),), ())
        first = rng.randrange(sides)
        offsets = [offset for offset in range(2, sides - 1)] or [2]
        second = (first + rng.choice(offsets)) % sides
        identification = EdgeGluing(
            EdgeRef(0, first), EdgeRef(0, second), "a", rng.choice((True, False))
        )
        return RandomSurfaceMorphismGenerator._build(source, (identification,), "self-boundary")

    @staticmethod
    def _close_annulus(rng: Random) -> BoundaryGluingMorphism:
        annulus_gluing = EdgeGluing(EdgeRef(0, 0), EdgeRef(0, 2), "a", False)
        source = SurfacePresentation((Polygon("C", 4),), (annulus_gluing,))
        identification = EdgeGluing(EdgeRef(0, 1), EdgeRef(0, 3), "b", rng.choice((True, False)))
        return RandomSurfaceMorphismGenerator._build(source, (identification,), "annulus-closure")

    @staticmethod
    def _build(
        source: SurfacePresentation,
        identifications: tuple[EdgeGluing, ...],
        family: str = "boundary-quotient",
    ) -> BoundaryGluingMorphism:
        target = SurfacePresentation(
            source.polygons, (*source.gluings, *identifications), source.paths
        )
        SurfaceAnalyzer().analyze(source)
        SurfaceAnalyzer().analyze(target)
        return BoundaryGluingMorphism(source, target, identifications, family)
