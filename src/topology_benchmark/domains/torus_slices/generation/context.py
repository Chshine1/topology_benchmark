from attrs import field, frozen

from topology_benchmark.core.probability.sampling import SamplingSession
from topology_benchmark.core.problem.models import GenerationRequest
from topology_benchmark.core.validation import number_range


@frozen
class UnlinkedTorusFamily:
    count: int = field(
        validator=number_range(
            minimum=1,
            maximum=4,
            message="an unlinked torus family needs between one and four components",
        )
    )


@frozen
class PairLinkedTorusFamily:
    count: int = field(
        validator=number_range(
            minimum=2,
            maximum=4,
            message="a pair-linked torus family needs between two and four components",
        )
    )


@frozen
class ChainLinkedTorusFamily:
    count: int = field(
        validator=number_range(
            minimum=3,
            maximum=4,
            message="a torus chain needs between three and four components",
        )
    )


@frozen
class CompletelyLinkedTorusFamily:
    count: int = field(
        validator=number_range(
            minimum=3,
            maximum=4,
            message="a completely linked torus family needs between three and four components",
        )
    )


type TorusFamilyCondition = (
    UnlinkedTorusFamily
    | PairLinkedTorusFamily
    | ChainLinkedTorusFamily
    | CompletelyLinkedTorusFamily
)


@frozen
class TorusGenerationContext:
    request: GenerationRequest
    condition: TorusFamilyCondition
    sampling: SamplingSession
