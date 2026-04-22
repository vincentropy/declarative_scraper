"""
Pydantic models for the declarative scraper.
"""

from __future__ import annotations

import enum
from typing import Union

from pydantic import Field

from .yaml import BaseModelWithYamlSupport
from ..processors import ProcessorName


class ProcessorSpec(BaseModelWithYamlSupport):
    """A single field processor.

    Can be a simple named processor (e.g. "strip") or a parameterised one, eg a regex.
    """

    name: ProcessorName
    args: list[str] = Field(default_factory=list)


class FieldType(enum.Enum):
    """Type of field to extract, used to determine how to extract it from HTML."""

    TEXT = "text"
    LINK = "link"
    NUMBER = "number"
    DATE = "date"
    OBJECT = "object"


class FieldSpec(BaseModelWithYamlSupport):
    """Specification for extracting a single field from HTML."""

    selector: str = Field(
        description="""
            CSS selector or XPATH selector for the field.
            If the fields attribute is not None, this selector should return a parent element or a list of parent elements.
            The selector attribute of the child fields will be applied relative to each parent element.
        """
    )
    type: FieldType = Field(
        default=FieldType.TEXT,
        description="Type of field to extract, used to validate extraction.",
    )
    required: bool = Field(default=True, description="Whether this field is required. Used for validation.")

    multiple: bool = Field(
        default=False,
        description="Whether to extract multiple values from this field (i.e. return a list).",
    )
    processors: list[Union[ProcessorName, dict[ProcessorName, list[str]]]] = Field(
        default_factory=list,
        description="List of processors to apply to the extracted value(s). Each processor can be a string (processor name) or a dict mapping processor name to argument list. These are applied in order.",
    )
    fields: dict[str, "FieldSpec"] | None = Field(
        default=None,
        description="Child fields to extract from the element(s) selected by this field. \
            Keys in this dict will be keys in the output data.",
    )

    def resolved_processors(self) -> list[ProcessorSpec]:
        """Normalise the processor list into ProcessorSpec objects from dict[func-name=>arg list] or str."""
        result: list[ProcessorSpec] = []
        for p in self.processors:
            if isinstance(p, (str, ProcessorName)):
                result.append(ProcessorSpec(name=p))
            elif isinstance(p, dict):
                for name, args in p.items():
                    result.append(ProcessorSpec(name=name, args=args))
            else:
                raise ValueError(f"Invalid processor spec: {p}")
        return result


class ParseSpec(BaseModelWithYamlSupport):
    """Top-level declarative parser specification."""

    version: int = 1
    name: str
    fields: dict[str, FieldSpec]
