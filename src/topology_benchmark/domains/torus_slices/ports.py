from __future__ import annotations

from random import Random
from typing import TYPE_CHECKING, Protocol

from topology_benchmark.core.models import GenerationRequest
from topology_benchmark.core.protocols import Representation
from topology_benchmark.domains.torus_slices.models import TorusSliceObservation

if TYPE_CHECKING:
    from topology_benchmark.domains.torus_slices.generation import TorusGenerationSpec


class TorusSliceGenerator(Protocol):
    def generate(
        self,
        request: GenerationRequest,
        rng: Random,
        spec: TorusGenerationSpec,
    ) -> TorusSliceObservation: ...


class TorusSliceRepresentation(Representation[TorusSliceObservation], Protocol):
    pass
