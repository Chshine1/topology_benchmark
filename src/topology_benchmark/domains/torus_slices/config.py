from attrs import field, frozen, validators


@frozen
class TorusCountConfig:
    easy_maximum: int = field(default=2, validator=validators.ge(1))
    standard_maximum: int = field(default=3, validator=validators.ge(1))
    linked_probability: float = field(
        default=0.58,
        validator=validators.and_(validators.ge(0.0), validators.le(1.0)),
    )


@frozen
class TorusLinkConfig:
    minimum_count: int = field(
        default=2,
        validator=validators.and_(validators.ge(2), validators.le(4)),
    )
    maximum_count: int = field(
        default=4,
        validator=validators.and_(validators.ge(2), validators.le(4)),
    )
    chain_probability: float = field(
        default=0.4,
        validator=validators.and_(validators.ge(0.0), validators.le(1.0)),
    )
    complete_probability: float = field(
        default=0.4,
        validator=validators.and_(validators.ge(0.0), validators.le(1.0)),
    )

    def __attrs_post_init__(self) -> None:
        if self.minimum_count > self.maximum_count:
            raise ValueError("torus link counts must lie between two and four")
        if self.chain_probability + self.complete_probability > 1:
            raise ValueError("torus link pattern probabilities are invalid")


@frozen
class TorusDomainConfig:
    count: TorusCountConfig = field(factory=TorusCountConfig)
    link: TorusLinkConfig = field(factory=TorusLinkConfig)
