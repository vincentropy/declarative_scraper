"""Core extraction engine that applies a ParseSpec to HTML content."""

from __future__ import annotations

from typing import cast

from bs4 import BeautifulSoup, Tag

from .models import EngineOutput, FieldSpec, ParseSpec, ProcessorSpec, DataValue
from .processors import apply_processor
from .uni_selector import select


class ParseEngine:
    """Applies a ParseSpec to HTML content and returns extracted items."""

    def __init__(self, spec: ParseSpec) -> None:
        self.spec = spec

    def parse(self, html: str, field_path: str | None = None) -> EngineOutput:
        """Parse HTML string and return EngineOutput with typed fields.

        Args:
            html: Raw HTML content to parse.
            field_path: Optional dot-separated path (e.g. ``"person.name"``) to
                extract only a single field instead of the full spec.  Each
                segment must match a key in the ``fields`` dict at that level of
                nesting.  Raises ``KeyError`` if a segment is not found or if a
                non-leaf segment has no child fields.
        """
        root = BeautifulSoup(html, "html.parser")
        if field_path is not None:
            data = self._extract_field_path(root, self.spec.fields, field_path.split("."))
        else:
            data = self._extract_fields(root, self.spec.fields)
        return EngineOutput(spec=self.spec, data=data if data is not None else {})

    def parse_and_validate(self, html: str, field_path: str | None = None) -> EngineOutput:
        """Parse HTML and validate output against spec, returning EngineOutput with validation results.
        Raises ValueError if validation fails."""
        from .validation.spec_validate import validate_spec_output  # pylint: disable=import-outside-toplevel

        output = self.parse(html, field_path=field_path)
        validate_spec_output(self.spec, output.data, raise_=True)
        return output

    @staticmethod
    def _extract_field_path(
        node: Tag | BeautifulSoup,
        fields: dict[str, FieldSpec],
        path: list[str],
    ) -> dict[str, DataValue]:
        """Navigate ``fields`` and the HTML tree simultaneously following ``path``.

        Returns a ``{leaf_name: value}`` dict containing only the targeted field.
        Raises ``KeyError`` if any path segment is missing or if a non-leaf
        segment has no child ``fields``.
        """
        name, *rest = path
        if name not in fields:
            raise KeyError(f"Field {name!r} not found. Available: {list(fields.keys())}")
        field_spec = fields[name]

        if not rest:
            # Leaf — extract just this field
            value = ParseEngine._extract_field(node, field_spec)
            return {name: value} if value is not None else {}

        # Intermediate — must have child fields and a navigable selector
        if field_spec.fields is None:
            raise KeyError(
                f"Field {name!r} has no child fields; cannot navigate to {'.'.join(rest)!r}"
            )
        sub_nodes = select(node, field_spec.selector, assert_tags=True)
        if not sub_nodes:
            return {}

        if field_spec.multiple:
            items = [
                ParseEngine._extract_field_path(sub, field_spec.fields, rest)
                for sub in sub_nodes
            ]
            return cast(dict[str, DataValue], {name: cast(DataValue, items)})

        inner = ParseEngine._extract_field_path(sub_nodes[0], field_spec.fields, rest)
        return cast(dict[str, DataValue], {name: cast(DataValue, inner)})

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

        all_strings = all(isinstance(v, str) for v in values)
        if all_strings:
            values = ["".join(cast(list[str], values))]
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
            return [] if field_spec.multiple else None

        if field_spec.multiple:
            # Return a list of FieldOutput objects
            return [ParseEngine._extract_fields(sub, field_spec.fields) for sub in sub_nodes]

        if len(sub_nodes) > 1:
            print(f"Warning: Multiple elements matched for single field: {field_spec.selector}. Using first match.")
        return ParseEngine._extract_fields(sub_nodes[0], field_spec.fields)

    @staticmethod
    def apply_processors(value: object, processors: list[ProcessorSpec]) -> str | float | None:
        if value is None:
            return value
        for proc in processors:
            value = apply_processor(proc.name, value, proc.args if proc.args else None)
        if isinstance(value, (str, float)):
            return value
        raise ValueError(f"Unsupported value type after processing: {type(value)}")
