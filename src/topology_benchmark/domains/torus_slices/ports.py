from typing import Protocol

from topology_benchmark.core.generation.object_generator import IConditionalGenerator
from topology_benchmark.core.presentation.representation import IRepresentation
from topology_benchmark.domains.torus_slices.generation.context import TorusGenerationContext
from topology_benchmark.domains.torus_slices.models.torus import TorusSliceObservation


class ITorusSliceGenerator(
    IConditionalGenerator[TorusGenerationContext, TorusSliceObservation],
    Protocol,
):
    pass


class ITorusSliceRepresentation(IRepresentation[TorusSliceObservation], Protocol):
    pass
