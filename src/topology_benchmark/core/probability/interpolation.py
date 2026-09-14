from itertools import pairwise


def interpolate_anchors(anchors: tuple[tuple[int, float], ...], difficulty: int) -> float:
    if not anchors:
        raise ValueError("an interpolated profile needs anchors")
    ordered = tuple(sorted(anchors))
    if difficulty <= ordered[0][0]:
        return ordered[0][1]
    if difficulty >= ordered[-1][0]:
        return ordered[-1][1]
    for (left_level, left), (right_level, right) in pairwise(ordered):
        if left_level <= difficulty <= right_level:
            fraction = (difficulty - left_level) / (right_level - left_level)
            return left + fraction * (right - left)
    raise AssertionError("difficulty was not bracketed")


def blended_weight(aligned: float, baseline: float, noise_probability: float) -> float:
    if min(aligned, baseline) < 0 or not 0 <= noise_probability <= 1:
        raise ValueError("weights must be nonnegative and noise must be a probability")
    return (1 - noise_probability) * aligned + noise_probability * baseline
