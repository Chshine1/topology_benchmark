"""Questions about objects and first-class quotient morphisms."""

from topology_benchmark.domains.surfaces.models import (
    SurfaceMorphism,
    SurfacePresentation,
)


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
        "path-representative": (
            f"Give a cellular homology representative for path {path.name if path else 'p'} "
            "in the deterministic spanning-forest cycle basis."
        ),
    }
    return questions[kind]


def morphism_questions(morphism: SurfaceMorphism) -> tuple[str, ...]:
    del morphism
    return (
        "euler-change",
        "boundary-change",
        "component-change",
        "target-homology",
        "map-injective",
        "map-surjective",
        "homology-isomorphism",
        "target-orientable",
    )


def formulate_morphism(kind: str) -> str:
    questions = {
        "euler-change": "For the displayed quotient map, what is χ(target) - χ(source)?",
        "boundary-change": (
            "For the displayed quotient map, what is b(target) - b(source), where b counts "
            "boundary components?"
        ),
        "component-change": (
            "For the displayed quotient map, what is the change in connected-component count?"
        ),
        "target-homology": "Compute the integral homology groups of the quotient target.",
        "map-injective": "Is the displayed map injective?",
        "map-surjective": "Is the displayed map surjective?",
        "homology-isomorphism": (
            "Does the displayed map induce isomorphisms on all homology groups?"
        ),
        "target-orientable": "Is every component of the quotient target orientable?",
    }
    return questions[kind]
