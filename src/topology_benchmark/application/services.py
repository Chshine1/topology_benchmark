"""Public benchmark use cases for object and morphism subjects."""

from random import Random

from topology_benchmark.core.models import GenerationRequest, Problem
from topology_benchmark.domains.surfaces.components.invariant import (
    morphism_answer,
    object_answer,
)
from topology_benchmark.domains.surfaces.components.question import (
    formulate_morphism,
    formulate_object,
    morphism_questions,
    object_questions,
)
from topology_benchmark.domains.surfaces.ports import (
    SurfaceAnswer,
    SurfaceGenerator,
    SurfaceMorphismGenerator,
    SurfaceRepresentation,
)


class SurfaceBenchmark:
    def __init__(
        self,
        generator: SurfaceGenerator,
        morphism_generator: SurfaceMorphismGenerator,
        representation: SurfaceRepresentation,
    ) -> None:
        self._generator = generator
        self._morphism_generator = morphism_generator
        self._representation = representation

    def generate(self, *, seed: int, difficulty: int = 1) -> Problem[SurfaceAnswer]:
        request = GenerationRequest(seed=seed, difficulty=difficulty)
        rng = Random(seed)
        question_rng = Random(seed ^ 0x5F3759DF)
        if difficulty >= 3 and question_rng.random() < 0.5:
            return self._morphism_problem(request, rng, question_rng)
        return self._object_problem(request, rng, question_rng)

    def _object_problem(
        self, request: GenerationRequest, rng: Random, question_rng: Random
    ) -> Problem[SurfaceAnswer]:
        surface = self._generator.generate(request, rng)
        kind = question_rng.choice(object_questions(surface))
        path_index = question_rng.randrange(len(surface.paths)) if surface.paths else 0
        prompt = self._representation.render(surface, request, Random(0))
        return Problem(
            question=formulate_object(surface, kind, path_index),
            prompts=(prompt,),
            answer=object_answer(surface, kind, path_index),
            seed=request.seed,
            metadata={
                "difficulty": request.difficulty,
                "subject": "object",
                "question_kind": kind,
                "visual_parameters_generated": True,
                "renderer_randomness": False,
            },
        )

    def _morphism_problem(
        self, request: GenerationRequest, rng: Random, question_rng: Random
    ) -> Problem[SurfaceAnswer]:
        morphism = self._morphism_generator.generate(request, rng)
        kind = question_rng.choice(morphism_questions(morphism))
        prompts = (
            self._representation.render(morphism.source, request, Random(0)),
            self._representation.render(morphism.target, request, Random(0)),
        )
        return Problem(
            question=(
                f"The first image is the source and the second is the target of the "
                f"{morphism.name}. " + formulate_morphism(kind)
            ),
            prompts=prompts,
            answer=morphism_answer(morphism, kind),
            seed=request.seed,
            metadata={
                "difficulty": request.difficulty,
                "subject": "morphism",
                "morphism": morphism.name,
                "question_kind": kind,
                "identified_edge_pairs": len(morphism.identifications),
                "visual_parameters_generated": True,
                "renderer_randomness": False,
            },
        )
