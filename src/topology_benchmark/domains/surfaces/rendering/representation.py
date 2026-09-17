from random import Random
from typing import override

from topology_benchmark.core.problem.models import GenerationRequest, QuestionSection
from topology_benchmark.domains.surfaces.abstractions import (
    ISurfaceRenderBackend,
    ISurfaceRepresentation,
)
from topology_benchmark.domains.surfaces.models import SurfacePresentation
from topology_benchmark.domains.surfaces.rendering.diagram_planner import SurfaceDiagramPlanner


class SurfaceRepresentation(ISurfaceRepresentation):
    def __init__(
        self,
        planner: SurfaceDiagramPlanner,
        backend: ISurfaceRenderBackend,
    ) -> None:
        self._planner = planner
        self._backend = backend

    @override
    def render(
        self,
        obj: SurfacePresentation,
        request: GenerationRequest,
        rng: Random,
    ) -> QuestionSection:
        del rng
        plan = self._planner.plan(obj, Random((request.seed << 8) ^ 0xA53C9E))
        return self._backend.render(obj, plan, request)
