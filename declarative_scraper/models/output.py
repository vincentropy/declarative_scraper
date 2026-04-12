from __future__ import annotations
from typing import Union

from pydantic import BaseModel

from .parser_spec import ParseSpec

type SingleDataValue = Union[str, float]
type DataValue = Union[SingleDataValue, list[SingleDataValue], dict[str, "DataValue"], list[dict[str, "DataValue"]]]


class EngineOutput(BaseModel):
    spec: ParseSpec
    data: dict[str, DataValue]
