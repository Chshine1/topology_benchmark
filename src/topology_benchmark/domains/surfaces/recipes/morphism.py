from abc import ABC, abstractmethod
from typing import override

from topology_benchmark.core.probability.sampling import SamplingSession
from topology_benchmark.core.problem.models import GenerationRequest, Problem
from topology_benchmark.core.problem.recipe import IProblemRecipe
from topology_benchmark.domains.surfaces.abstractions import (
    ISurfaceMorphismGenerator,
    ISurfaceRepresentation,
    SurfaceAnswer,
)
from topology_benchmark.domains.surfaces.generation.config import SurfaceGenerationConfig
from topology_benchmark.domains.surfaces.generation.context.morphism import (
    SurfaceMorphismGenerationContext,
)
from topology_benchmark.domains.surfaces.models import (
    BoundaryGluingMorphism,
    PolygonAttachmentMorphism,
    SurfaceMorphism,
)
from topology_benchmark.domains.surfaces.recipes.homology import integral_homology
from topology_benchmark.domains.surfaces.services import SurfaceAnalyzer


class SurfaceMorphismProblemRecipe(IProblemRecipe[SurfaceAnswer], ABC):
    id = ""
    prompt = ""

    def __init__(
        self,
        generator: ISurfaceMorphismGenerator,
        representation: ISurfaceRepresentation,
        analyzer: SurfaceAnalyzer,
        config: SurfaceGenerationConfig,
    ) -> None:
        self._generator = generator
        self._representation = representation
        self._analyzer = analyzer
        self._config = config
        self._morphism_law = config.morphism_law_for(self.id)

    @override
    def generate(self, request: GenerationRequest) -> Problem[SurfaceAnswer]:
        sampling = SamplingSession(request.seed, self._config.profile_version)
        context = SurfaceMorphismGenerationContext(
            request,
            self._morphism_law.at(request.difficulty),
            sampling,
        )
        morphism = self._generator.generate_for(context)
        sections = tuple(
            self._representation.render(obj, request, sampling.rng(f"render.{name}"))
            for name, obj in (("source", morphism.source), ("target", morphism.target))
        )
        prompt = (
            "The first diagram is the source and the second is the target of the indicated "
            f"{morphism.name.replace('-', ' ')}. {self.prompt}"
        )
        return Problem(prompt, sections, self._answer(morphism), request.seed, self.id)

    @abstractmethod
    def _answer(self, morphism: SurfaceMorphism, /) -> SurfaceAnswer: ...


class EulerChangeProblemRecipe(SurfaceMorphismProblemRecipe):
    id, prompt = "euler-change", "What is chi(target) - chi(source)?"

    @override
    def _answer(self, morphism: SurfaceMorphism, /) -> SurfaceAnswer:
        return (
            self._analyzer.analyze(morphism.target).euler_characteristic
            - self._analyzer.analyze(morphism.source).euler_characteristic
        )


class BoundaryChangeProblemRecipe(SurfaceMorphismProblemRecipe):
    id, prompt = "boundary-change", "What is the target boundary count minus the source count?"

    @override
    def _answer(self, morphism: SurfaceMorphism, /) -> SurfaceAnswer:
        return (
            self._analyzer.analyze(morphism.target).boundary_components
            - self._analyzer.analyze(morphism.source).boundary_components
        )


class ComponentChangeProblemRecipe(SurfaceMorphismProblemRecipe):
    id, prompt = "component-change", "What is the target component count minus the source count?"

    @override
    def _answer(self, morphism: SurfaceMorphism, /) -> SurfaceAnswer:
        return len(self._analyzer.analyze(morphism.target).components) - len(
            self._analyzer.analyze(morphism.source).components
        )


class TargetHomologyProblemRecipe(SurfaceMorphismProblemRecipe):
    id, prompt = "target-homology", "Compute the integral homology of the target."

    @override
    def _answer(self, morphism: SurfaceMorphism, /) -> SurfaceAnswer:
        return integral_homology(self._analyzer, morphism.target)


class MapInjectiveProblemRecipe(SurfaceMorphismProblemRecipe):
    id, prompt = "map-injective", "Is this map injective on surface points?"

    @override
    def _answer(self, morphism: SurfaceMorphism, /) -> SurfaceAnswer:
        return isinstance(morphism, PolygonAttachmentMorphism)


class MapSurjectiveProblemRecipe(SurfaceMorphismProblemRecipe):
    id, prompt = "map-surjective", "Is this map surjective onto the target?"

    @override
    def _answer(self, morphism: SurfaceMorphism, /) -> SurfaceAnswer:
        return isinstance(morphism, BoundaryGluingMorphism)


class HomologyIsomorphismProblemRecipe(SurfaceMorphismProblemRecipe):
    id, prompt = "homology-isomorphism", "Does this map induce integral homology isomorphisms?"

    @override
    def _answer(self, morphism: SurfaceMorphism, /) -> SurfaceAnswer:
        return isinstance(morphism, PolygonAttachmentMorphism)


class TargetOrientableProblemRecipe(SurfaceMorphismProblemRecipe):
    id, prompt = "target-orientable", "Is every target component orientable?"

    @override
    def _answer(self, morphism: SurfaceMorphism, /) -> SurfaceAnswer:
        return all(
            component.orientable for component in self._analyzer.analyze(morphism.target).components
        )
