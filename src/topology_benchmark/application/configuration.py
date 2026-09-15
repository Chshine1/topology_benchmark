import sys
from pathlib import Path


def _config_directory() -> Path:
    project_directory = Path(__file__).parents[3] / "config"
    if project_directory.is_dir():
        return project_directory
    return Path(sys.prefix) / "share" / "topology_benchmark" / "config"


PROJECT_CONFIG_DIRECTORY = _config_directory()
SURFACE_DOMAIN_CONFIG = PROJECT_CONFIG_DIRECTORY / "surfaces.yaml"
POLYHEDRAL_DOMAIN_CONFIG = PROJECT_CONFIG_DIRECTORY / "polyhedral-nets.yaml"
TORUS_DOMAIN_CONFIG = PROJECT_CONFIG_DIRECTORY / "torus-slices.yaml"
