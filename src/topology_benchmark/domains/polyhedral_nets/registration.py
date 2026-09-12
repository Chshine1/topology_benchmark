from lagom import Container, Singleton

from topology_benchmark.domains.polyhedral_nets.analysis import PolyhedralNetAnalyzer
from topology_benchmark.domains.polyhedral_nets.generation import RandomPolyhedralNetGenerator
from topology_benchmark.domains.polyhedral_nets.representation import PolyhedralNetSvgRenderer


def add_polyhedral_nets_domain(container: Container) -> Container:
    container[RandomPolyhedralNetGenerator] = RandomPolyhedralNetGenerator
    container[PolyhedralNetAnalyzer] = Singleton(PolyhedralNetAnalyzer)
    container[PolyhedralNetSvgRenderer] = PolyhedralNetSvgRenderer
    return container
