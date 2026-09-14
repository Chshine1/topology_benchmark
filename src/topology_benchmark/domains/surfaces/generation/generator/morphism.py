from random import Random
from typing import override

from topology_benchmark.core.errors import GenerationExhaustedError
from topology_benchmark.core.probability.distribution import TruncatedGeometricDistribution
from topology_benchmark.core.problem.models import GenerationRequest
from topology_benchmark.domains.surfaces.generation.config import SurfaceGenerationConfig
from topology_benchmark.domains.surfaces.generation.context.morphism import (
    AnnulusClosureCondition,
    AttachmentCondition,
    FullDiskBoundaryCondition,
    PartialIntercomponentCondition,
    SelfBoundaryCondition,
    SurfaceMorphismGenerationContext,
)
from topology_benchmark.domains.surfaces.models import (
    BoundaryGluingMorphism,
    EdgeGluing,
    EdgeRef,
    Polygon,
    PolygonAttachmentMorphism,
    SurfaceMorphism,
    SurfacePresentation,
)
from topology_benchmark.domains.surfaces.ports import ISurfaceMorphismGenerator
from topology_benchmark.domains.surfaces.services import SurfaceAnalyzer


class RandomSurfaceMorphismGenerator(ISurfaceMorphismGenerator):
    def __init__(self, config: SurfaceGenerationConfig, analyzer: SurfaceAnalyzer) -> None:
        self.config = config
        self._analyzer = analyzer

    @override
    def generate_for(self, context: SurfaceMorphismGenerationContext) -> SurfaceMorphism:
        return self._generate(context, context.sampling.rng("morphism.structure"))

    def _generate(self, context: SurfaceMorphismGenerationContext, rng: Random) -> SurfaceMorphism:
        condition = context.sampling.sample("morphism.condition", context.law)
        for _ in range(self.config.morphism_retry_limit):
            try:
                if isinstance(condition, FullDiskBoundaryCondition):
                    sides = self._side_count(context.request, rng)
                    return self._glue_two_disks(rng, sides)
                if isinstance(condition, AttachmentCondition):
                    return self._attach_polygon(rng)
                if isinstance(condition, PartialIntercomponentCondition):
                    return self._partial_intercomponent(rng, context.request.difficulty)
                if isinstance(condition, SelfBoundaryCondition):
                    return self._self_boundary(rng, context.request.difficulty)
                if isinstance(condition, AnnulusClosureCondition):
                    return self._close_annulus(rng)
                raise AssertionError("unknown surface morphism condition")
            except ValueError:
                continue
        raise GenerationExhaustedError(
            "surfaces",
            f"realize the {condition.family_id} morphism condition",
            self.config.morphism_retry_limit,
        )

    def _side_count(self, request: GenerationRequest, rng: Random) -> int:
        continuation = self.config.difficulty.side_continuation.at(request.difficulty)
        return TruncatedGeometricDistribution(3, 8, continuation).sample(rng)

    def _attach_polygon(self, rng: Random) -> PolygonAttachmentMorphism:
        source_sides, attached_sides = rng.randint(3, 6), rng.randint(3, 6)
        source = SurfacePresentation((Polygon("D", source_sides),), ())
        attachment = EdgeGluing(EdgeRef(0, 1), EdgeRef(1, 0), "a", False)
        target = SurfacePresentation(
            (Polygon("D", source_sides), Polygon("A", attached_sides)), (attachment,)
        )
        self._analyzer.analyze(target)
        return PolygonAttachmentMorphism(source, target, attachment, 1, "attachment")

    def _glue_two_disks(self, rng: Random, sides: int) -> BoundaryGluingMorphism:
        del rng
        polygons = (Polygon("D1", sides), Polygon("D2", sides))
        source = SurfacePresentation(polygons, ())
        identifications = tuple(
            EdgeGluing(EdgeRef(0, edge), EdgeRef(1, sides - 1 - edge), f"g{edge + 1}", False)
            for edge in range(sides)
        )
        return self._build(source, identifications, "full-disk-boundary")

    def _partial_intercomponent(self, rng: Random, difficulty: int) -> BoundaryGluingMorphism:
        first_sides, second_sides = rng.randint(3, 7), rng.randint(3, 7)
        source = SurfacePresentation((Polygon("D1", first_sides), Polygon("D2", second_sides)), ())
        maximum = min(first_sides, second_sides) - 1
        count = rng.randint(1, min(maximum, 1 + difficulty // 3))
        identifications = tuple(
            EdgeGluing(EdgeRef(0, edge), EdgeRef(1, count - 1 - edge), f"g{edge + 1}", False)
            for edge in range(count)
        )
        return self._build(source, identifications, "partial-intercomponent")

    def _self_boundary(self, rng: Random, difficulty: int) -> BoundaryGluingMorphism:
        sides = rng.randint(4, min(8, 4 + difficulty // 2))
        source = SurfacePresentation((Polygon("D", sides),), ())
        first = rng.randrange(sides)
        offsets = [offset for offset in range(2, sides - 1)] or [2]
        second = (first + rng.choice(offsets)) % sides
        identification = EdgeGluing(
            EdgeRef(0, first), EdgeRef(0, second), "a", rng.choice((True, False))
        )
        return self._build(source, (identification,), "self-boundary")

    def _close_annulus(self, rng: Random) -> BoundaryGluingMorphism:
        annulus_gluing = EdgeGluing(EdgeRef(0, 0), EdgeRef(0, 2), "a", False)
        source = SurfacePresentation((Polygon("C", 4),), (annulus_gluing,))
        identification = EdgeGluing(EdgeRef(0, 1), EdgeRef(0, 3), "b", rng.choice((True, False)))
        return self._build(source, (identification,), "annulus-closure")

    def _build(
        self,
        source: SurfacePresentation,
        identifications: tuple[EdgeGluing, ...],
        family: str = "boundary-quotient",
    ) -> BoundaryGluingMorphism:
        target = SurfacePresentation(
            source.polygons, (*source.gluings, *identifications), source.paths
        )
        self._analyzer.analyze(source)
        self._analyzer.analyze(target)
        return BoundaryGluingMorphism(source, target, identifications, family)
