from __future__ import annotations

from typing import TypeAliasType, Union  # pylint: disable=unused-import

from declarative_scraper.models.yaml import BaseModelWithYamlSupport

from .parser_spec import ParseSpec

DataValue = TypeAliasType(
    "DataValue",
    "Union[None, float, str, dict[str, DataValue], list[str], list[float], list[dict[str, DataValue]]]",
)


class EngineOutput(BaseModelWithYamlSupport):
    """Output from the scraping engine for a single file,
    including the parser spec used and the extracted data."""

    spec: ParseSpec | None = None
    data: dict[str, DataValue]
