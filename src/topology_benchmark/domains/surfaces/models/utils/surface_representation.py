from topology_benchmark.domains.surfaces import SurfacePresentation, OrientedEdge


def edges_connected(polygon_sides: int, first: OrientedEdge, second: OrientedEdge) -> bool:
    return (first.edge.edge + (1 if first.forward else -1)) % polygon_sides == second.edge.edge
