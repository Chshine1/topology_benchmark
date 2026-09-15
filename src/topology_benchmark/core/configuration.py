from pathlib import Path
from typing import cast

import yaml
from pydantic import BaseModel

from topology_benchmark.core.errors import ConfigurationError


def load_yaml_config[ConfigT: BaseModel](path: str | Path, config_type: type[ConfigT]) -> ConfigT:
    config_path = Path(path)
    with config_path.open(encoding="utf-8") as stream:
        value = cast(object, yaml.safe_load(stream))
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ConfigurationError(f"{config_path} must be a YAML mapping with string keys")
    return config_type.model_validate(value)
