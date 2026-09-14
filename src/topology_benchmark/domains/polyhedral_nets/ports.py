from random import Random
from typing import Protocol, override

from topology_benchmark.core.generation.object_generator import IObjectGenerator
from topology_benchmark.core.presentation.representation import IRepresentation
from topology_benchmark.core.problem.models import GenerationRequest, QuestionSection
from topology_benchmark.domains.polyhedral_nets.models.net import PolyhedralFolding, PolyhedralNet

type PolyhedralAnswer = int | str | bool


class IPolyhedralNetGenerator(IObjectGenerator[PolyhedralFolding], Protocol):
    pass


class IPolyhedralNetRepresentation(IRepresentation[PolyhedralNet], Protocol):
    @override
    def render(
        self,
        obj: PolyhedralNet,
        request: GenerationRequest,
        rng: Random,
        *,
        scale: float | None = None,
    ) -> QuestionSection: ...
