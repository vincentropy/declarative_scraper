from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel

T = TypeVar("T", bound="BaseModelWithYamlSupport")


class BaseModelWithYamlSupport(BaseModel):
    """BaseModel subclass with support for loading from YAML files."""

    @classmethod
    def from_yaml_file(cls: type[T], file_path: Path) -> T:
        """Load a model instance from a YAML file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)

    def to_yaml_file(self, file_path: Path) -> None:
        """Save a model instance to a YAML file."""
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.model_dump(), f)
