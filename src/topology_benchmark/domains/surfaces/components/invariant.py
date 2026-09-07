"""Invariants computed from surface objects and boundary-gluing morphisms."""

from topology_benchmark.domains.surfaces.analysis import SurfaceAnalyzer, SurfaceFacts
from topology_benchmark.domains.surfaces.models import (
    BoundaryGluingMorphism,
    PolygonAttachmentMorphism,
    SurfaceMorphism,
    SurfacePresentation,
)
from topology_benchmark.domains.surfaces.ports import SurfaceAnswer


def integral_homology(surface: SurfacePresentation) -> str:
    return _homology_from_facts(SurfaceAnalyzer().analyze(surface))


def object_answer(
    surface: SurfacePresentation, question_kind: str, path_index: int = 0
) -> SurfaceAnswer:
    analyzer = SurfaceAnalyzer()
    facts = analyzer.analyze(surface)
    if question_kind == "euler-characteristic":
        return facts.euler_characteristic
    if question_kind == "boundary-components":
        return facts.boundary_components
    if question_kind == "connected-components":
        return len(facts.components)
    if question_kind == "orientable":
        return all(component.orientable for component in facts.components)
    if question_kind == "homology-groups":
        return _homology_from_facts(facts)
    path = surface.paths[path_index]
    if question_kind == "path-is-cycle":
        return analyzer.path_is_cycle(surface, path)
    if question_kind == "path-representative":
        if not analyzer.path_is_cycle(surface, path):
            return "not a homology class (the path is not a cycle)"
        labels = analyzer.cycle_basis(surface)
        vector = analyzer.path_representative(surface, path)
        return f"edge_basis={tuple(labels)}; cycle={vector} mod cellular boundaries"
    raise ValueError(f"unknown surface question kind: {question_kind}")


def morphism_answer(morphism: SurfaceMorphism, question_kind: str) -> SurfaceAnswer:
    analyzer = SurfaceAnalyzer()
    source = analyzer.analyze(morphism.source)
    target = analyzer.analyze(morphism.target)
    if question_kind == "euler-change":
        return target.euler_characteristic - source.euler_characteristic
    if question_kind == "boundary-change":
        return target.boundary_components - source.boundary_components
    if question_kind == "component-change":
        return len(target.components) - len(source.components)
    if question_kind == "target-homology":
        return _homology_from_facts(target)
    if question_kind == "map-injective":
        return isinstance(morphism, PolygonAttachmentMorphism)
    if question_kind == "map-surjective":
        return isinstance(morphism, BoundaryGluingMorphism)
    if question_kind == "homology-isomorphism":
        # The attachment retracts across the added disc; generated boundary
        # quotients change H0, H1, or H2.
        return isinstance(morphism, PolygonAttachmentMorphism)
    if question_kind == "target-orientable":
        return all(component.orientable for component in target.components)
    raise ValueError(f"unknown morphism question kind: {question_kind}")


def _homology_from_facts(facts: SurfaceFacts) -> str:
    h0 = _free_group(len(facts.components))
    h1_rank = sum(component.first_betti_number for component in facts.components)
    torsion = sum(
        not component.orientable and component.boundary_components == 0
        for component in facts.components
    )
    h1_parts = []
    if h1_rank:
        h1_parts.append(_free_group(h1_rank))
    if torsion:
        h1_parts.append("Z/2" if torsion == 1 else f"(Z/2)^{torsion}")
    h2_rank = sum(
        component.orientable and component.boundary_components == 0
        for component in facts.components
    )
    return f"H_0={h0}; H_1={' ⊕ '.join(h1_parts) or '0'}; H_2={_free_group(h2_rank)}"


def _free_group(rank: int) -> str:
    if rank == 0:
        return "0"
    return "Z" if rank == 1 else f"Z^{rank}"
