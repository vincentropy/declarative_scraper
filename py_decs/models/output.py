from __future__ import annotations

from typing import TypeAliasType, Union  # pylint: disable=unused-import

from .yaml import BaseModelWithYamlSupport

from .parser_spec import ParseSpec

DataValue = TypeAliasType(
    "DataValue",
    "Union[None, float, str, dict[str, DataValue], list[DataValue]]",
)


class EngineOutput(BaseModelWithYamlSupport):
    """Output from the scraping engine for a single file,
    including the parser spec used and the extracted data."""

    spec: ParseSpec | None = None
    data: dict[str, DataValue]
