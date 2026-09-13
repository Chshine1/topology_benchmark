from random import Random
from typing import Protocol, override

from topology_benchmark.core.models import GenerationRequest, QuestionSection
from topology_benchmark.core.protocols import ObjectGenerator, Representation
from topology_benchmark.domains.polyhedral_nets.models import PolyhedralFolding, PolyhedralNet


class PolyhedralNetGenerator(ObjectGenerator[PolyhedralFolding], Protocol):
    pass


class PolyhedralNetRepresentation(Representation[PolyhedralNet], Protocol):
    @override
    def render(
        self,
        obj: PolyhedralNet,
        request: GenerationRequest,
        rng: Random,
        *,
        scale: float | None = None,
    ) -> QuestionSection: ...
