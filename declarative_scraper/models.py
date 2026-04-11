"""
Pydantic models for the declarative scraper.
"""

import enum
from typing import TypeVar, Union

import yaml
from pydantic import BaseModel, Field

T = TypeVar("T", bound="BaseModelWithYamlSupport")


class BaseModelWithYamlSupport(BaseModel):
    """BaseModel subclass with support for loading from YAML files."""

    @classmethod
    def model_validate_yaml(cls: type[T], file_path: str) -> T:
        """Load a model instance from a YAML file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)


class ProcessorSpec(BaseModelWithYamlSupport):
    """A single field processor.

    Can be a simple named processor (e.g. "strip") or a parameterised one, eg a regex.
    """

    name: str
    args: list[str] = Field(default_factory=list)


class FieldType(enum.Enum):
    """Type of field to extract, used to determine how to extract it from HTML."""

    TEXT = "text"
    LINK = "link"
    NUMBER = "number"


class FieldSpec(BaseModelWithYamlSupport):
    """Specification for extracting a single field from HTML."""

    selector: str = Field(
        description="""
            CSS selector for the field.
            If the fields attribute is not None, this selector should return a parent element or a list of parent elements.
            The selector attribute of the child fields will be applied relative to each parent element.
        """
    )
    type: FieldType = Field(
        default=FieldType.TEXT,
        description="Type of field to extract, used to validate extraction.",
    )
    required: bool = Field(
        default=True, description="Whether this field is required. Used for validation."
    )

    multiple: bool = Field(
        default=False,
        description="Whether to extract multiple values from this field (i.e. return a list).",
    )
    processors: list[Union[str, dict[str, str]]] = Field(
        default_factory=list,
        description="List of processors to apply to the extracted value(s). \
            These are applied in order.",
    )
    fields: dict[str, "FieldSpec"] | None = Field(
        default=None,
        description="Child fields to extract from the element(s) selected by this field. \
            Keys in this dict will be keys in the output data.",
    )

    def resolved_processors(self) -> list[ProcessorSpec]:
        """Normalise the mixed-format processor list into ProcessorSpec objects."""
        result: list[ProcessorSpec] = []
        for p in self.processors:
            if isinstance(p, str):
                result.append(ProcessorSpec(name=p))
            elif isinstance(p, dict):
                for name, arg in p.items():
                    result.append(ProcessorSpec(name=name, args=[arg]))
        return result


class ParseSpec(BaseModelWithYamlSupport):
    """Top-level declarative parser specification."""

    version: int = 1
    name: str
    fields: dict[str, FieldSpec]
