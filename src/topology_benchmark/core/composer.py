"""Default orchestration of the domain-independent generation workflow."""

from random import Random

from topology_benchmark.core.models import GenerationRequest, Problem
from topology_benchmark.core.protocols import ProblemComposer
from topology_benchmark.core.recipe import ProblemRecipe


class DefaultProblemComposer(ProblemComposer):
    def compose[ObjectT, AnswerT](
        self,
        recipe: ProblemRecipe[ObjectT, AnswerT],
        request: GenerationRequest,
    ) -> Problem[AnswerT]:
        rng = Random(request.seed)
        obj = recipe.generator.generate(request, rng)
        transformations: list[str] = []
        for transformation in recipe.transformations:
            obj = transformation.apply(obj, request, rng)
            transformations.append(transformation.name)

        answer = recipe.invariant.compute(obj)
        prompt = recipe.representation.render(obj, request, rng)
        problem = Problem(
            question=recipe.question.formulate(recipe.invariant.name),
            prompts=(prompt,),
            answer=answer,
            seed=request.seed,
            metadata={
                "difficulty": request.difficulty,
                "invariant": recipe.invariant.name,
                "transformations": ",".join(transformations),
            },
        )
        self._validate(problem)
        return problem

    @staticmethod
    def _validate[AnswerT](problem: Problem[AnswerT]) -> None:
        if not problem.question.strip():
            raise ValueError("a generated problem must have a question")
        if not problem.prompts:
            raise ValueError("a generated problem must have a representation")
        if any(not prompt.content.strip() for prompt in problem.prompts):
            raise ValueError("a generated representation must not be empty")
