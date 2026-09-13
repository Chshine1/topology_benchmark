from abc import ABC, abstractmethod
from typing import override

from topology_benchmark.core.models import GenerationRequest, Problem
from topology_benchmark.core.probability import SamplingSession
from topology_benchmark.core.protocols import ProblemRecipe
from topology_benchmark.domains.surfaces.analysis import SurfaceAnalyzer
from topology_benchmark.domains.surfaces.components.generation_config import SurfaceGenerationConfig
from topology_benchmark.domains.surfaces.components.invariant import integral_homology
from topology_benchmark.domains.surfaces.generation import (
    PathGenerationMode,
    QuestionFocus,
    SurfaceObjectGenerationContext,
    SurfaceObjectGenerationSpec,
)
from topology_benchmark.domains.surfaces.models import (
    EdgeRef,
    SurfacePresentation,
)
from topology_benchmark.domains.surfaces.ports import (
    SurfaceAnswer,
    SurfaceGenerator,
    SurfaceRepresentation,
)


class SurfaceObjectQuestion(ProblemRecipe[SurfaceAnswer], ABC):
    id = ""
    focus = QuestionFocus.GLOBAL
    path_mode = PathGenerationMode.NONE
    favor_multiple_polygons = False

    def __init__(
        self,
        generator: SurfaceGenerator,
        representation: SurfaceRepresentation,
        analyzer: SurfaceAnalyzer,
        config: SurfaceGenerationConfig,
    ) -> None:
        self._generator = generator
        self._representation = representation
        self._analyzer = analyzer
        self._config = config

    @override
    def generate(self, request: GenerationRequest) -> Problem[SurfaceAnswer]:
        sampling = SamplingSession(request.seed, self._config.profile_version)
        context = SurfaceObjectGenerationContext(
            request,
            SurfaceObjectGenerationSpec(
                self.focus,
                self.path_mode,
                self.favor_multiple_polygons,
            ),
            sampling,
        )
        surface = self._generator.generate_for(context)
        section = self._representation.render(
            surface,
            request,
            sampling.rng("render.object"),
            edge_labels=self._edge_labels(surface),
        )
        return Problem(
            self._question(surface),
            (section,),
            self._answer(surface),
            request.seed,
            self.id,
        )

    @abstractmethod
    def _question(self, surface: SurfacePresentation, /) -> str: ...

    @abstractmethod
    def _answer(self, surface: SurfacePresentation, /) -> SurfaceAnswer: ...

    def _edge_labels(self, _surface: SurfacePresentation, /) -> tuple[tuple[EdgeRef, str], ...]:
        return ()


class EulerCharacteristicQuestion(SurfaceObjectQuestion):
    id = "euler-characteristic"

    @override
    def _question(self, _surface: SurfacePresentation, /) -> str:
        return "What is the Euler characteristic of the glued surface?"

    @override
    def _answer(self, surface: SurfacePresentation, /) -> SurfaceAnswer:
        return self._analyzer.analyze(surface).euler_characteristic


class BoundaryComponentsQuestion(SurfaceObjectQuestion):
    id = "boundary-components"

    @override
    def _question(self, _surface: SurfacePresentation, /) -> str:
        return "How many boundary components remain after all marked gluings?"

    @override
    def _answer(self, surface: SurfacePresentation, /) -> SurfaceAnswer:
        return self._analyzer.analyze(surface).boundary_components


class ConnectedComponentsQuestion(SurfaceObjectQuestion):
    id = "connected-components"
    favor_multiple_polygons = True

    @override
    def _question(self, _surface: SurfacePresentation, /) -> str:
        return "How many connected components does the quotient surface have?"

    @override
    def _answer(self, surface: SurfacePresentation, /) -> SurfaceAnswer:
        return len(self._analyzer.analyze(surface).components)


class OrientableQuestion(SurfaceObjectQuestion):
    id = "orientable"
    focus = QuestionFocus.CLASSIFICATION

    @override
    def _question(self, _surface: SurfacePresentation, /) -> str:
        return "Is every connected component of the quotient surface orientable?"

    @override
    def _answer(self, surface: SurfacePresentation, /) -> SurfaceAnswer:
        return all(component.orientable for component in self._analyzer.analyze(surface).components)


class HomologyGroupsQuestion(SurfaceObjectQuestion):
    id = "homology-groups"
    focus = QuestionFocus.CLASSIFICATION

    @override
    def _question(self, _surface: SurfacePresentation, /) -> str:
        return "Compute H_0, H_1, and H_2 with integer coefficients."

    @override
    def _answer(self, surface: SurfacePresentation, /) -> SurfaceAnswer:
        return integral_homology(self._analyzer, surface)


class PathIsCycleQuestion(SurfaceObjectQuestion):
    id = "path-is-cycle"
    focus = QuestionFocus.PATH
    path_mode = PathGenerationMode.CYCLE_TEST

    @override
    def _question(self, surface: SurfacePresentation, /) -> str:
        return f"Does the displayed path {surface.paths[0].name} define a 1-cycle?"

    @override
    def _answer(self, surface: SurfacePresentation, /) -> SurfaceAnswer:
        return self._analyzer.path_is_cycle(surface, surface.paths[0])


class PathRepresentativeQuestion(SurfaceObjectQuestion):
    id = "path-representative"
    focus = QuestionFocus.PATH
    path_mode = PathGenerationMode.REPRESENTATIVE

    @override
    def _question(self, surface: SurfacePresentation, /) -> str:
        generators = self._analyzer.h1_edge_generators(surface)
        used_edges = sorted(
            edge
            for edge in range(len(self._analyzer.cellular_homology(surface).edge_basis))
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
        names = ", ".join(f"h{index}" for index in range(1, len(generators) + 1))
        path_name = surface.paths[0].name
        return (
            "Each tagged arrow e1, e2, ... is the shown orientation of one quotient edge. "
            "Use the ordered generators of the invariant-factor decomposition of H_1 given by "
            f"{decomposition}. Give only the coefficient tuple of {path_name} in ({names}), with "
            "torsion coefficients reduced to their least nonnegative values."
        )

    @override
    def _answer(self, surface: SurfacePresentation, /) -> SurfaceAnswer:
        return self._analyzer.path_homology_coefficients(surface, surface.paths[0])

    @override
    def _edge_labels(self, surface: SurfacePresentation, /) -> tuple[tuple[EdgeRef, str], ...]:
        used = {
            edge
            for coefficients, _ in self._analyzer.h1_edge_generators(surface)
            for edge, coefficient in enumerate(coefficients)
            if coefficient
        }
        basis = self._analyzer.cellular_homology(surface).edge_basis
        return tuple((basis[edge], f"e{tag}") for tag, edge in enumerate(sorted(used), start=1))
