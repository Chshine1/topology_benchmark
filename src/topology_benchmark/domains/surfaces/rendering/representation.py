from collections.abc import Iterator, Mapping
from random import Random
from typing import override

from topology_benchmark.core.problem.models import GenerationRequest, QuestionSection
from topology_benchmark.domains.surfaces.abstractions import (
    ISurfaceRenderBackend,
    ISurfaceRepresentation,
)
from topology_benchmark.domains.surfaces.models import SurfacePresentation
from topology_benchmark.domains.surfaces.rendering.diagram_planner import SurfaceDiagramPlanner


class SurfaceRenderBackendCatalog(Mapping[str, ISurfaceRenderBackend]):
    def __init__(self, backends: Mapping[str, ISurfaceRenderBackend]) -> None:
        self._backends = dict(backends)

    @override
    def __getitem__(self, backend_id: str) -> ISurfaceRenderBackend:
        return self._backends[backend_id]

    @override
    def __iter__(self) -> Iterator[str]:
        return iter(self._backends)

    @override
    def __len__(self) -> int:
        return len(self._backends)


class SurfaceRepresentation(ISurfaceRepresentation):
    def __init__(
        self,
        planner: SurfaceDiagramPlanner,
        backends: SurfaceRenderBackendCatalog,
    ) -> None:
        self._planner = planner
        self._backends = backends

    @override
    def render(
        self,
        obj: SurfacePresentation,
        request: GenerationRequest,
        rng: Random,
    ) -> QuestionSection:
        del rng
        plan = self._planner.plan(obj, Random((request.seed << 8) ^ 0xA53C9E))
        return self._backends[plan.style.visual.backend].render(obj, plan, request)
