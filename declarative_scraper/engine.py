"""Core extraction engine that applies a ParseSpec to HTML content."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, NavigableString, Tag
import lxml.etree

from declarative_scraper.models.output import DataValue

from .models import FieldSpec, ParseSpec, ProcessorSpec, EngineOutput
from .processors import apply_processor

_PSEUDO_RE = re.compile(r"::(text|attr\(([^)]+)\))\s*$")


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

        values = ParseEngine._select(node, field_spec.selector)
        if not values:
            return [] if field_spec.multiple else None
        if field_spec.multiple:
            out_values = [ParseEngine.apply_processors(v, field_spec.resolved_processors()) for v in values]
            return out_values

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

        base, mode = ParseEngine._parse_selector(field_spec.selector)
        if mode is not None:
            print(f"Warning: Ignoring pseudo-selector {mode} on field with child fields: {field_spec.selector}")
        sub_nodes = node.select(base)
        if not sub_nodes:
            return None

        if field_spec.multiple:
            # Return a list of FieldOutput objects
            return [ParseEngine._extract_fields(sub, field_spec.fields) for sub in sub_nodes]

        if len(sub_nodes) > 1:
            print(f"Warning: Multiple elements matched for single field: {field_spec.selector}. Using first match.")
        return ParseEngine._extract_fields(sub_nodes[0], field_spec.fields)

    @staticmethod
    def _parse_selector(css: str) -> tuple[str, str | None]:
        """Split selector into (base, mode) stripping ::text / ::attr(...)."""
        m = _PSEUDO_RE.search(css)
        if not m:
            return css, None
        base = css[: m.start()]
        if m.group(1) == "text":
            return base, "text"
        return base, f"attr:{m.group(2)}"

    @staticmethod
    def _select_css(node: Tag | BeautifulSoup, css: str) -> list[str]:
        """Run a CSS selector and return matched strings."""

        base, mode = ParseEngine._parse_selector(css)
        tags = node.select(base) if base.strip() else []

        if mode == "text":
            results: list[str] = []
            for tag in tags:
                for child in tag.children:
                    if isinstance(child, NavigableString) and not isinstance(child, Tag):
                        results.append(str(child))
            return results

        if mode is not None and mode.startswith("attr:"):
            attr_name = mode[5:]
            results = []
            for tag in tags:
                val = tag.get(attr_name)
                if val is not None:
                    results.append(" ".join(val) if isinstance(val, list) else str(val))
            return results

        return [str(tag) for tag in tags]

    @staticmethod
    def _select(node: Tag | BeautifulSoup, selector: str) -> list[str]:
        """Select using either XPATH or CSS selector syntax."""

        try:
            # Try XPATH first, since it's more powerful and can be used to select attributes without needing ::attr(...)
            tree = lxml.etree.HTML(str(node))
            results = tree.xpath(selector)
            if results:
                return [str(r) for r in results]
        except lxml.etree.XPathError:
            pass
        # Fall back to CSS selector
        try:
            return ParseEngine._select_css(node, selector)
        except Exception:
            pass
        raise ValueError(f"Selector is not valid XPATH or CSS: {selector}")

    @staticmethod
    def apply_processors(value: object, processors: list[ProcessorSpec]) -> str | float:
        for proc in processors:
            value = apply_processor(proc.name, value, proc.args if proc.args else None)
        if isinstance(value, (str, float)):
            return value
        raise ValueError(f"Unsupported value type after processing: {type(value)}")
