from dataclasses import dataclass
from random import Random

from topology_benchmark.core.probability.distribution import FiniteDistribution, WeightedValue
from topology_benchmark.domains.surfaces.rendering.config import (
    PaletteConfig,
    SurfaceRenderingConfig,
    SurfaceVisualStyleConfig,
)


@dataclass(frozen=True, slots=True)
class SelectedVisualStyle:
    profile: SurfaceVisualStyleConfig
    palette: PaletteConfig


class SurfaceVisualStyleSelector:
    def __init__(self, config: SurfaceRenderingConfig) -> None:
        self._distribution = FiniteDistribution(
            tuple(WeightedValue(style, style.weight) for style in config.styles)
        )

    @property
    def distribution(self) -> FiniteDistribution[SurfaceVisualStyleConfig]:
        return self._distribution

    def select(self, rng: Random) -> SelectedVisualStyle:
        profile = self._distribution.sample(rng)
        return SelectedVisualStyle(profile, rng.choice(profile.palettes))
