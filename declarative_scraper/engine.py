"""Core extraction engine that applies a ParseSpec to HTML content."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, NavigableString, Tag

from .models import FieldSpec, ParseSpec, ProcessorSpec
from .processors import apply_processor

_PSEUDO_RE = re.compile(r"::(text|attr\(([^)]+)\))\s*$")


class ParseEngine:
    """Applies a ParseSpec to HTML content and returns extracted items."""

    def __init__(self, spec: ParseSpec) -> None:
        self.spec = spec

    def parse(self, html: str) -> list[dict[str, object]]:
        """Parse HTML string and return a list of extracted item dicts."""
        root = BeautifulSoup(html, "html.parser")
        return [self._extract_fields(root, self.spec.fields)]

    @staticmethod
    def _extract_fields(node: Tag | BeautifulSoup, fields: dict[str, FieldSpec]) -> dict[str, object]:
        result: dict[str, object] = {}
        for name, field_spec in fields.items():
            result[name] = ParseEngine._extract_field(node, field_spec)
        return result

    @staticmethod
    def _extract_field(node: Tag | BeautifulSoup, field_spec: FieldSpec) -> object:
        if field_spec.fields is not None:
            # if this field has child fields, extraction is slightly different
            # we ignore ::text / ::attr on the parent selector.
            return ParseEngine._extract_nested(node, field_spec)

        css = field_spec.selector
        values = ParseEngine._select(node, css)
        if not values:
            return [] if field_spec.multiple else None
        if field_spec.multiple:
            return [ParseEngine.apply_processors(v, field_spec.resolved_processors()) for v in values]

        if len(values) > 1:
            print(f"Warning: Multiple elements matched for single field: {css}. Using first match.")
        return ParseEngine.apply_processors(values[0], field_spec.resolved_processors())

    @staticmethod
    def _extract_nested(node: Tag | BeautifulSoup, field_spec: FieldSpec) -> object:
        """Extract a field with child fields, applying child selectors relative to parent elements.
        In this case we ignore ::text / ::attr on the parent selector since it doesn't make sense
        to apply these to a parent element that we're extracting child fields from."""
        assert field_spec.fields is not None

        css = field_spec.selector
        base, mode = ParseEngine._parse_selector(css)
        if mode is not None:
            print(f"Warning: Ignoring pseudo-selector {mode} on field with child fields: {css}")
        sub_nodes = node.select(base)
        if not sub_nodes:
            return [] if field_spec.multiple else None

        if field_spec.multiple:
            return [ParseEngine._extract_fields(sub, field_spec.fields) for sub in sub_nodes]

        if len(sub_nodes) > 1:
            print(f"Warning: Multiple elements matched for single field: {css}. Using first match.")
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
    def _select(node: Tag | BeautifulSoup, css: str) -> list[str]:
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
    def apply_processors(value: object, processors: list[ProcessorSpec]) -> object:
        for proc in processors:
            value = apply_processor(proc.name, value, proc.args if proc.args else None)
        return value
