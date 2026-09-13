import sys
from pathlib import Path


def _config_directory() -> Path:
    project_directory = Path(__file__).parents[3] / "config"
    if project_directory.is_dir():
        return project_directory
    return Path(sys.prefix) / "share" / "topology_benchmark" / "config"


PROJECT_CONFIG_DIRECTORY = _config_directory()
SURFACE_GENERATION_DEFAULTS = PROJECT_CONFIG_DIRECTORY / "surfaces" / "generation.yaml"
SURFACE_RENDERING_DEFAULTS = PROJECT_CONFIG_DIRECTORY / "surfaces" / "rendering.yaml"
