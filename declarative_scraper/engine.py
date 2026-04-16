"""Core extraction engine that applies a ParseSpec to HTML content."""

from __future__ import annotations
from typing import cast

from bs4 import BeautifulSoup, Tag

from declarative_scraper.models.output import DataValue

from .models import EngineOutput, FieldSpec, ParseSpec, ProcessorSpec
from .processors import apply_processor
from .uni_selector import select


class ParseEngine:
    """Applies a ParseSpec to HTML content and returns extracted items."""

    def __init__(self, spec: ParseSpec) -> None:
        self.spec = spec

    def parse(self, html: str) -> EngineOutput:
        """Parse HTML string and return EngineOutput with typed fields."""
        root = BeautifulSoup(html, "html.parser")
        fields = self._extract_fields(root, self.spec.fields)
        # fields is a FieldOutput with .fields as a dict[str, FieldOutput]
        # EngineOutput expects fields: dict[str, FieldOutput]
        return EngineOutput(spec=self.spec, data=fields if fields is not None else {})

    @staticmethod
    def _extract_fields(node: Tag | BeautifulSoup, fields: dict[str, FieldSpec]) -> dict[str, DataValue]:
        result: dict[str, DataValue] = {}
        for name, field_spec in fields.items():
            field_out = ParseEngine._extract_field(node, field_spec)
            if field_out is not None:
                result[name] = field_out
        return result

    @staticmethod
    def _extract_field(node: Tag | BeautifulSoup, field_spec: FieldSpec) -> DataValue | None:
        if field_spec.fields is not None:
            # if this field has child fields, extraction is slightly different
            # we ignore ::text / ::attr on the parent selector.
            return ParseEngine._extract_nested(node, field_spec)

        values = select(node, field_spec.selector)
        if not values:
            return [] if field_spec.multiple else None
        if field_spec.multiple:
            out_values = [ParseEngine.apply_processors(v, field_spec.resolved_processors()) for v in values]
            return cast(DataValue, out_values)

        if len(values) > 1:
            print(f"Warning: Multiple elements matched for single field: {field_spec.selector}. Using first match.")
        out_value = ParseEngine.apply_processors(values[0], field_spec.resolved_processors())
        return out_value

    @staticmethod
    def _extract_nested(node: Tag | BeautifulSoup, field_spec: FieldSpec) -> DataValue | None:
        """Extract a field with child fields, applying child selectors relative to parent elements.
        In this case we ignore ::text / ::attr on the parent selector since it doesn't make sense
        to apply these to a parent element that we're extracting child fields from."""
        assert field_spec.fields is not None

        sub_nodes = select(node, field_spec.selector, assert_tags=True)
        if not sub_nodes:
            return None

        if field_spec.multiple:
            # Return a list of FieldOutput objects
            return [ParseEngine._extract_fields(sub, field_spec.fields) for sub in sub_nodes]

        if len(sub_nodes) > 1:
            print(f"Warning: Multiple elements matched for single field: {field_spec.selector}. Using first match.")
        return ParseEngine._extract_fields(sub_nodes[0], field_spec.fields)

    @staticmethod
    def apply_processors(value: object, processors: list[ProcessorSpec]) -> str | float:
        for proc in processors:
            value = apply_processor(proc.name, value, proc.args if proc.args else None)
        if isinstance(value, (str, float)):
            return value
        raise ValueError(f"Unsupported value type after processing: {type(value)}")
