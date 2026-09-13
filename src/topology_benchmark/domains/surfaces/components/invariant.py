from collections import Counter

from topology_benchmark.domains.surfaces.analysis import SurfaceAnalyzer
from topology_benchmark.domains.surfaces.models import SurfacePresentation


def integral_homology(analyzer: SurfaceAnalyzer, surface: SurfacePresentation) -> str:
    homology = analyzer.cellular_homology(surface)
    h1_parts = []
    if homology.h1_rank:
        h1_parts.append(_free_group(homology.h1_rank))
    for order, count in sorted(Counter(homology.h1_torsion).items()):
        h1_parts.append(f"Z/{order}" if count == 1 else f"(Z/{order})^{count}")
    return (
        f"H_0={_free_group(homology.h0_rank)}; "
        f"H_1={' ⊕ '.join(h1_parts) or '0'}; H_2={_free_group(homology.h2_rank)}"
    )


def _free_group(rank: int) -> str:
    if rank == 0:
        return "0"
    return "Z" if rank == 1 else f"Z^{rank}"
