"""Intent-first benchmark use cases for object and morphism subjects."""

from topology_benchmark.core.models import GenerationRequest, Problem
from topology_benchmark.core.probability import SamplingSession
from topology_benchmark.domains.surfaces.components.generation_config import (
    SurfaceGenerationConfig,
)
from topology_benchmark.domains.surfaces.components.invariant import (
    morphism_answer,
    object_answer,
)
from topology_benchmark.domains.surfaces.components.question import (
    formulate_morphism,
    formulate_object,
)
from topology_benchmark.domains.surfaces.generation import (
    ProblemSubject,
    SurfaceGenerationContext,
    SurfaceProblemIntent,
)
from topology_benchmark.domains.surfaces.models import SurfacePresentation
from topology_benchmark.domains.surfaces.ports import (
    SurfaceAnswer,
    SurfaceGenerator,
    SurfaceIntentGenerator,
    SurfaceMorphismGenerator,
    SurfaceRepresentation,
)


class SurfaceBenchmark:
    def __init__(
        self,
        generator: SurfaceGenerator,
        morphism_generator: SurfaceMorphismGenerator,
        representation: SurfaceRepresentation,
        intent_generator: SurfaceIntentGenerator,
        generation_config: SurfaceGenerationConfig,
    ) -> None:
        self._generator = generator
        self._morphism_generator = morphism_generator
        self._representation = representation
        self._intent_generator = intent_generator
        self._config = generation_config

    def generate(self, *, seed: int, difficulty: int = 1) -> Problem[SurfaceAnswer]:
        request = GenerationRequest(seed=seed, difficulty=difficulty)
        sampling = SamplingSession(seed, self._config.profile_version)
        intent = self._intent_generator.sample(request, sampling)
        context = SurfaceGenerationContext(request, intent, sampling)
        if intent.subject is ProblemSubject.MORPHISM:
            return self._morphism_problem(context)
        return self._object_problem(context)

    def _object_problem(self, context: SurfaceGenerationContext) -> Problem[SurfaceAnswer]:
        surface = self._generator.generate_for(context)
        prompt = self._representation.render(
            surface,
            context.request,
            context.sampling.rng("render.object"),
        )
        metadata = self._common_metadata(context.intent, context)
        metadata.update(self._surface_metadata(surface))
        return Problem(
            question=formulate_object(surface, context.intent.question_kind, 0),
            prompts=(prompt,),
            answer=object_answer(surface, context.intent.question_kind, 0),
            seed=context.request.seed,
            metadata=metadata,
        )

    def _morphism_problem(self, context: SurfaceGenerationContext) -> Problem[SurfaceAnswer]:
        morphism = self._morphism_generator.generate_for(context)
        prompts = (
            self._representation.render(
                morphism.source,
                context.request,
                context.sampling.rng("render.morphism.source"),
            ),
            self._representation.render(
                morphism.target,
                context.request,
                context.sampling.rng("render.morphism.target"),
            ),
        )
        metadata = self._common_metadata(context.intent, context)
        metadata.update(
            {
                "morphism": morphism.name,
                "morphism_family": morphism.family,
                "identified_edge_pairs": len(morphism.identifications),
                "source_polygons": len(morphism.source.polygons),
                "target_polygons": len(morphism.target.polygons),
            }
        )
        return Problem(
            question=formulate_morphism(context.intent.question_kind),
            prompts=prompts,
            answer=morphism_answer(morphism, context.intent.question_kind),
            seed=context.request.seed,
            metadata=metadata,
        )

    def _common_metadata(
        self,
        intent: SurfaceProblemIntent,
        context: SurfaceGenerationContext,
    ) -> dict[str, str | int | bool]:
        return {
            "difficulty": context.request.difficulty,
            "subject": intent.subject.value,
            "question_focus": intent.focus.value,
            "question_kind": intent.question_kind,
            "generation_profile": self._config.profile_version,
            "intentional_noise": intent.noise
            or any(event.noise for event in context.sampling.events),
            "sampling_trace": context.sampling.trace_json(),
            "visual_parameters_generated": False,
            "renderer_randomness": True,
        }

    @staticmethod
    def _surface_metadata(surface: SurfacePresentation) -> dict[str, int]:
        return {
            "polygon_count": len(surface.polygons),
            "polygon_edges": sum(polygon.sides for polygon in surface.polygons),
            "gluing_count": len(surface.gluings),
            "path_count": len(surface.paths),
            "path_segments": sum(len(path.edges) for path in surface.paths),
        }
