from lagom import Container, Singleton

from topology_benchmark.domains.torus_slices.analysis import TorusFamilyAnalyzer
from topology_benchmark.domains.torus_slices.generation import RandomTorusSliceGenerator
from topology_benchmark.domains.torus_slices.representation import TorusSliceSvgRenderer


def add_torus_slices_domain(container: Container) -> Container:
    container[RandomTorusSliceGenerator] = RandomTorusSliceGenerator
    container[TorusFamilyAnalyzer] = Singleton(TorusFamilyAnalyzer)
    container[TorusSliceSvgRenderer] = TorusSliceSvgRenderer
    return container
