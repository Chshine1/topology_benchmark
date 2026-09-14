import hashlib
from random import Random

from topology_benchmark.core.probability.distribution import IDistribution


class SamplingSession:
    """Give each namespace an independent RNG derived from the profile and seed."""

    def __init__(self, seed: int, profile_version: str) -> None:
        self.seed = seed
        self.profile_version = profile_version

    def rng(self, namespace: str) -> Random:
        material = f"{self.profile_version}\0{self.seed}\0{namespace}".encode()
        digest = hashlib.blake2b(material, digest_size=16).digest()
        return Random(int.from_bytes(digest, "big"))

    def sample[T](self, namespace: str, distribution: IDistribution[T]) -> T:
        return distribution.sample(self.rng(namespace))
