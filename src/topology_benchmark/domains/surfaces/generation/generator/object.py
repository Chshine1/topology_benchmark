import math
from random import Random
from typing import override

from topology_benchmark.core.probability.distribution import (
    BernoulliDistribution,
    FiniteDistribution,
    TruncatedGeometricDistribution,
    WeightedValue,
)
from topology_benchmark.core.probability.interpolation import blended_weight
from topology_benchmark.core.problem.models import GenerationRequest
from topology_benchmark.domains.surfaces.generation.config import SurfaceGenerationConfig
from topology_benchmark.domains.surfaces.generation.context.object import (
    DistinguishedSurfacePaths,
    NontrivialHomologySurfacePath,
    NoSurfacePaths,
    SurfaceObjectCondition,
    SurfaceObjectGenerationContext,
)
from topology_benchmark.domains.surfaces.models import (
    EdgeGluing,
    EdgeRef,
    OrientedEdge,
    Polygon,
    SurfacePath,
    SurfacePresentation,
)
from topology_benchmark.domains.surfaces.ports import ISurfaceGenerator
from topology_benchmark.domains.surfaces.services import SurfaceAnalyzer


class RandomSurfacePresentationGenerator(ISurfaceGenerator):
    def __init__(self, config: SurfaceGenerationConfig, analyzer: SurfaceAnalyzer) -> None:
        self.config = config
        self._analyzer = analyzer

    @override
    def generate_for(self, context: SurfaceObjectGenerationContext) -> SurfacePresentation:
        return self._generate(context, context.sampling.rng("surface.structure"))

    def _generate(
        self, context: SurfaceObjectGenerationContext, rng: Random
    ) -> SurfacePresentation:
        condition = context.sampling.sample("surface.condition", context.law)
        for _ in range(self.config.retry_limit):
            polygon_count = self._polygon_count(context, condition, rng)
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
                facts = self._analyzer.analyze(candidate)
            except ValueError:
                continue
            if len(facts.components) != condition.component_count:
                continue
            paths = self._paths(candidate, context, condition)
            completed = SurfacePresentation(polygons, gluings, paths)
            if isinstance(condition.paths, NontrivialHomologySurfacePath):
                facts = self._analyzer.analyze(completed)
                generators = self._analyzer.h1_edge_generators(completed)
                tagged_edges = {
                    edge
                    for coefficients, _ in generators
                    for edge, coefficient in enumerate(coefficients)
                    if coefficient
                }
                if (
                    len(facts.components) != 1
                    or not 1 <= len(generators) <= 3
                    or len(tagged_edges) > 8
                    or not any(self._analyzer.path_homology_coefficients(completed, paths[0]))
                ):
                    continue
            return completed

        if isinstance(condition.paths, NontrivialHomologySurfacePath):
            fallback = SurfacePresentation(
                (Polygon("P", 4),),
                (
                    EdgeGluing(EdgeRef(0, 0), EdgeRef(0, 2), "a"),
                    EdgeGluing(EdgeRef(0, 1), EdgeRef(0, 3), "b"),
                ),
                (SurfacePath("p", (OrientedEdge(EdgeRef(0, 0)),)),),
            )
            return fallback
        fallback_rng = context.sampling.rng("surface.fallback")
        polygons = tuple(
            Polygon(chr(ord("P") + index), 3 + fallback_rng.randrange(4))
            for index in range(condition.component_count)
        )
        fallback = SurfacePresentation(polygons, ())
        return SurfacePresentation(
            fallback.polygons,
            (),
            self._paths(fallback, context, condition),
        )

    def _polygon_count(
        self,
        context: SurfaceObjectGenerationContext,
        condition: SurfaceObjectCondition,
        rng: Random,
    ) -> int:
        profile = self.config.difficulty
        difficulty = context.request.difficulty
        target = profile.visual_budget.at(difficulty)
        options = []
        for count, weights in profile.polygon_count_weights.items():
            aligned = weights.at(difficulty)
            aligned *= 3.0 if count >= condition.component_count else 0.0
            if not isinstance(condition.paths, NoSurfacePaths) and count > 2:
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

    def _pair_count(
        self, context: SurfaceObjectGenerationContext, edge_count: int, rng: Random
    ) -> int:
        maximum = edge_count // 2
        density = self.config.difficulty.gluing_density.at(context.request.difficulty)
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
        self,
        surface: SurfacePresentation,
        context: SurfaceObjectGenerationContext,
        condition: SurfaceObjectCondition,
    ) -> tuple[SurfacePath, ...]:
        if isinstance(condition.paths, NoSurfacePaths):
            return ()
        count = (
            condition.paths.count if isinstance(condition.paths, DistinguishedSurfacePaths) else 1
        )
        paths: list[SurfacePath] = []
        remaining_segments = 7
        for index in range(count):
            reserved_for_later = count - index - 1
            maximum = remaining_segments - reserved_for_later
            path = self._path(surface, context, condition, index, maximum)
            paths.append(path)
            remaining_segments -= len(path.edges)
        return tuple(paths)

    def _path(
        self,
        surface: SurfacePresentation,
        context: SurfaceObjectGenerationContext,
        condition: SurfaceObjectCondition,
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
        if index == 0:
            must_be_closed = (
                condition.paths.first_closed
                if isinstance(condition.paths, DistinguishedSurfacePaths)
                else True
            )
        else:
            must_be_closed = context.sampling.sample(
                f"path.{index}.closed", BernoulliDistribution(0.5)
            )
        rng = context.sampling.rng(f"path.{index}.walk")
        quotient = surface.quotient_vertices()
        directed = tuple(
            OrientedEdge(EdgeRef(polygon, edge), forward)
            for polygon, shape in enumerate(surface.polygons)
            for edge in range(shape.sides)
            for forward in (True, False)
        )
        outgoing: dict[int, list[OrientedEdge]] = {}
        for edge in directed:
            start = surface.path_endpoint(edge, True, quotient)
            outgoing.setdefault(start, []).append(edge)
        for _ in range(80):
            walk = [rng.choice(directed)]
            for _ in range(length - 1):
                current = surface.path_endpoint(walk[-1], False, quotient)
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
            closed = surface.path_endpoint(walk[0], True, quotient) == surface.path_endpoint(
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
                    if surface.path_endpoint(item, True, quotient)
                    != surface.path_endpoint(item, False, quotient)
                ),
                directed[0],
            )
            walk = (edge,)
        return SurfacePath(chr(ord("p") + index), walk)

    @staticmethod
    def _label(index: int) -> str:
        alphabet = "abcdefghijklmnopqrstuvwxyz"
        return alphabet[index] if index < len(alphabet) else f"g{index + 1}"
