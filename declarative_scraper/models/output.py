from __future__ import annotations
from typing import Any, Union

from pydantic import BaseModel

from .parser_spec import ParseSpec

SingleDataValue = Union[str, float]
DataValue = Union[SingleDataValue, list[SingleDataValue], dict[str, "DataValue"], list[dict[str, "DataValue"]]]


class EngineOutput(BaseModel):
    """Output from the scraping engine for a single file,
    including the parser spec used and the extracted data."""

    spec: ParseSpec
    # TODO: introduce stronger typing or validation for this field.
    data: dict[str, Any]
