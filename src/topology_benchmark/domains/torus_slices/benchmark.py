"""Application service for spatial reasoning from torus level sections."""

from topology_benchmark.core.models import GenerationRequest, Problem
from topology_benchmark.core.probability import SamplingSession
from topology_benchmark.domains.torus_slices.analysis import TorusFamilyAnalyzer
from topology_benchmark.domains.torus_slices.generation import RandomTorusSliceGenerator
from topology_benchmark.domains.torus_slices.representation import TorusSliceSvgRenderer

type TorusSliceAnswer = int | bool


class TorusSlicesBenchmark:
    """Ask topological questions while revealing only finitely many parallel slices."""

    profile_version = "torus-slices-v1"

    def __init__(
        self,
        generator: RandomTorusSliceGenerator,
        analyzer: TorusFamilyAnalyzer,
        representation: TorusSliceSvgRenderer,
    ) -> None:
        self._generator = generator
        self._analyzer = analyzer
        self._representation = representation

    def generate(self, *, seed: int, difficulty: int = 1) -> Problem[TorusSliceAnswer]:
        request = GenerationRequest(seed, difficulty)
        sampling = SamplingSession(seed, self.profile_version)
        kind = self._question_kind(difficulty, sampling.rng("intent.question-kind").random())
        rng = sampling.rng("object.structure")
        if kind == "torus-count":
            maximum = 2 if difficulty <= 3 else 3
            count = rng.randint(1, maximum)
            linked: bool | None = None
        elif kind == "linked":
            count = 2
            linked = bool(rng.randrange(2))
        else:
            count = rng.randint(2, 4)
            linked = bool(rng.randrange(2))
        observation = self._generator.generate(request, rng, count=count, linked=linked)
        linked_pairs = self._analyzer.linked_pairs(observation.family)
        if kind == "torus-count":
            question = (
                "The panels are aligned horizontal sections of one hidden family of pairwise-"
                "disjoint rigid round tori. How many tori are in the family?"
            )
            answer: TorusSliceAnswer = len(observation.family.tori)
        elif kind == "linked":
            question = (
                "These aligned sections come from exactly two pairwise-disjoint rigid round "
                "tori. Are their core circles linked?"
            )
            answer = bool(linked_pairs)
        elif kind == "completely-unlinked":
            question = (
                "Do these level sections force every pair of core circles to have linking "
                "number zero?"
            )
            answer = not linked_pairs
        else:
            question = (
                "How many unordered pairs of the hidden tori have core circles with nonzero "
                "linking number?"
            )
            answer = len(linked_pairs)
        sampling.note("intent.question-kind", kind)
        prompt = self._representation.render(
            observation, request, sampling.rng("render.level-sections")
        )
        return Problem(
            question=question,
            prompts=(prompt,),
            answer=answer,
            seed=seed,
            metadata={
                "difficulty": difficulty,
                "domain": "torus-slices",
                "subject": "torus-family",
                "question_kind": kind,
                "generation_profile": self.profile_version,
                "sampling_trace": sampling.trace_json(),
                "pairwise_disjoint_certified": True,
                "rigid_round_tori": True,
                "height_direction_shown": True,
                "hidden_equations": True,
            },
        )

    @staticmethod
    def _question_kind(difficulty: int, choice: float) -> str:
        if difficulty <= 2:
            return "torus-count"
        if difficulty <= 5:
            return "linked" if choice < 0.65 else "torus-count"
        if difficulty <= 7:
            return "completely-unlinked" if choice < 0.5 else "linked-pair-count"
        return "linked-pair-count" if choice < 0.75 else "completely-unlinked"
