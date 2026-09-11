"""Questions about polygonal surface objects."""

from topology_benchmark.domains.surfaces.analysis import SurfaceAnalyzer
from topology_benchmark.domains.surfaces.models import SurfacePresentation


def object_questions(surface: SurfacePresentation) -> tuple[str, ...]:
    kinds = [
        "euler-characteristic",
        "boundary-components",
        "connected-components",
        "orientable",
        "homology-groups",
    ]
    if surface.paths:
        kinds.extend(("path-is-cycle", "path-representative"))
    return tuple(kinds)


def formulate_object(surface: SurfacePresentation, kind: str, path_index: int = 0) -> str:
    path = surface.paths[path_index] if surface.paths else None
    questions = {
        "euler-characteristic": "What is the Euler characteristic of the glued surface?",
        "boundary-components": "How many boundary components remain after all marked gluings?",
        "connected-components": "How many connected components does the quotient surface have?",
        "orientable": "Is every connected component of the quotient surface orientable?",
        "homology-groups": "Compute H_0, H_1, and H_2 with integer coefficients.",
        "path-is-cycle": f"Does the displayed path {path.name if path else 'p'} define a 1-cycle?",
        "path-representative": _path_coordinate_question(surface, path_index),
    }
    return questions[kind]


def _path_coordinate_question(surface: SurfacePresentation, path_index: int) -> str:
    analyzer = SurfaceAnalyzer()
    generators = analyzer.h1_edge_generators(surface)
    used_edges = sorted(
        edge
        for edge in range(len(analyzer.cellular_homology(surface).edge_basis))
        if any(coefficients[edge] for coefficients, _ in generators)
    )
    edge_tags = {edge: index + 1 for index, edge in enumerate(used_edges)}
    definitions = []
    for index, (coefficients, order) in enumerate(generators, start=1):
        terms = []
        for edge, coefficient in enumerate(coefficients):
            if not coefficient:
                continue
            magnitude = abs(coefficient)
            tag = edge_tags[edge]
            term = f"e{tag}" if magnitude == 1 else f"{magnitude}e{tag}"
            if not terms:
                terms.append(term if coefficient > 0 else f"-{term}")
            else:
                terms.append((" + " if coefficient > 0 else " - ") + term)
        expression = "".join(terms) or "0"
        suffix = " (infinite order)" if order is None else f" (order {order})"
        definitions.append(f"h{index} = {expression}{suffix}")
    decomposition = "; ".join(definitions) if definitions else "H_1 = 0"
    generator_names = ", ".join(f"h{index}" for index in range(1, len(generators) + 1))
    path_name = surface.paths[path_index].name if surface.paths else "p"
    return (
        "Each tagged arrow e1, e2, ... is the shown orientation of one quotient edge. "
        f"Use the ordered generators of the invariant-factor decomposition of H_1 given by "
        f"{decomposition}. Give only the coefficient tuple of {path_name} in "
        f"({generator_names}), with torsion coefficients reduced to their least nonnegative values."
    )
