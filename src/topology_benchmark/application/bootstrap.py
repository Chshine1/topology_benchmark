"""Lagom composition root; this is the only module aware of concrete adapters."""

from lagom import Container

from topology_benchmark.core.composer import DefaultProblemComposer
from topology_benchmark.core.protocols import ProblemComposer
from topology_benchmark.domains.surfaces.components.generator import (
    RandomSurfaceMorphismGenerator,
    RandomSurfacePresentationGenerator,
)
from topology_benchmark.domains.surfaces.components.representation import SvgGluingDiagramRenderer
from topology_benchmark.domains.surfaces.ports import (
    SurfaceGenerator,
    SurfaceMorphismGenerator,
    SurfaceRepresentation,
)


def build_container() -> Container:
    container = Container()
    container[ProblemComposer] = DefaultProblemComposer
    container[SurfaceGenerator] = RandomSurfacePresentationGenerator
    container[SurfaceMorphismGenerator] = RandomSurfaceMorphismGenerator
    container[SurfaceRepresentation] = SvgGluingDiagramRenderer
    return container
