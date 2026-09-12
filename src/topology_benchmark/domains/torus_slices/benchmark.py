from topology_benchmark.core.models import GenerationRequest, Problem
from topology_benchmark.core.probability import SamplingSession
from topology_benchmark.core.protocols import ProblemProvider
from topology_benchmark.domains.torus_slices.analysis import TorusFamilyAnalyzer
from topology_benchmark.domains.torus_slices.generation import RandomTorusSliceGenerator
from topology_benchmark.domains.torus_slices.representation import TorusSliceSvgRenderer

type TorusSliceAnswer = int | bool


class TorusSlicesBenchmark(ProblemProvider):
    profile_version = "torus-slices-v2"

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
        link_pattern = None
        if linked and count >= 3 and difficulty >= 7:
            pattern_choice = rng.random()
            link_pattern = (
                "chain" if pattern_choice < 0.4 else "complete" if pattern_choice < 0.8 else "pairs"
            )
        observation = self._generator.generate(
            request,
            rng,
            count=count,
            linked=linked,
            link_pattern=link_pattern,
        )
        linked_pairs = self._analyzer.linked_pairs(observation.family)
        if kind == "torus-count":
            question = (
                "The panels are aligned horizontal sections of one hidden family of pairwise-"
                "disjoint tori with planar elliptic cores. How many tori are in the family?"
            )
            answer: TorusSliceAnswer = len(observation.family.tori)
        elif kind == "linked":
            question = (
                "These aligned sections come from exactly two pairwise-disjoint elliptic "
                "tori. Are their core curves linked?"
            )
            answer = bool(linked_pairs)
        elif kind == "completely-unlinked":
            question = (
                "In the hidden generated family, does every pair of core curves have linking "
                "number zero?"
            )
            answer = not linked_pairs
        elif kind == "linked-pair-count":
            question = (
                "How many unordered pairs of the hidden tori have core curves with nonzero "
                "linking number?"
            )
            answer = len(linked_pairs)
        else:
            raise RuntimeError(f"unsupported torus-slice question kind: {kind}")
        section = self._representation.render(
            observation, request, sampling.rng("render.level-sections")
        )
        return Problem(
            question=question,
            sections=(section,),
            answer=answer,
            seed=seed,
            question_kind=kind,
        )

    @staticmethod
    def _question_kind(difficulty: int, choice: float) -> str:
        if difficulty <= 2:
            return "torus-count"
        if difficulty <= 5:
            return "linked" if choice < 0.65 else "torus-count"
        if difficulty <= 7:
            return "completely-unlinked" if choice < 0.5 else "linked-pair-count"
        if difficulty == 8:
            return "linked-pair-count" if choice < 0.75 else "completely-unlinked"
        return "linked-pair-count" if choice < 0.72 else "completely-unlinked"
