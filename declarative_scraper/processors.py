"""Built-in field processors for transforming extracted values."""

from __future__ import annotations

import re
from enum import Enum
from typing import Callable, Literal, overload


class ProcessorName(Enum):
    STRIP = "strip"
    TO_INT = "to_int"
    TO_FLOAT = "to_float"
    LOWERCASE = "lowercase"
    UPPERCASE = "uppercase"
    JOIN = "join"
    REGEX = "regex"
    SPLIT = "split"
    INDEX = "index"


def regex_extract(value: str, pattern: str) -> str:
    """Extract the first regex match from value. Returns empty string if no match."""
    match = re.search(pattern, value)
    return match.group(0) if match else ""


def split_string(value: str, separator: str = " ") -> list[str]:
    """Split a string by the given separator."""
    return value.split(separator)


def select_index(value: list[object], idx: str) -> object:
    """Select an element from a list by index."""
    return value[int(idx)]


PROCESSOR_REGISTRY: dict[ProcessorName, Callable[..., object]] = {
    ProcessorName.STRIP: lambda value: value.strip(),
    ProcessorName.TO_INT: int,
    ProcessorName.TO_FLOAT: float,
    ProcessorName.LOWERCASE: lambda value: value.lower(),
    ProcessorName.UPPERCASE: lambda value: value.upper(),
    ProcessorName.JOIN: lambda value, separator=" ": separator.join(value),
    ProcessorName.REGEX: regex_extract,
    ProcessorName.SPLIT: split_string,
    ProcessorName.INDEX: select_index,
}


@overload
def apply_processor(name: Literal[ProcessorName.STRIP], value: str) -> str: ...
@overload
def apply_processor(name: Literal[ProcessorName.TO_INT], value: str) -> int: ...
@overload
def apply_processor(name: Literal[ProcessorName.TO_FLOAT], value: str) -> float: ...
@overload
def apply_processor(name: Literal[ProcessorName.LOWERCASE], value: str) -> str: ...
@overload
def apply_processor(name: Literal[ProcessorName.UPPERCASE], value: str) -> str: ...
@overload
def apply_processor(name: Literal[ProcessorName.JOIN], value: list[str], args: list[str] | None = None) -> str: ...
@overload
def apply_processor(name: Literal[ProcessorName.REGEX], value: str, args: list[str] | None = None) -> str: ...
@overload
def apply_processor(name: Literal[ProcessorName.SPLIT], value: str, args: list[str] | None = None) -> list[str]: ...
@overload
def apply_processor(
    name: Literal[ProcessorName.INDEX],
    value: list[object],
    args: list[str],
) -> object: ...
@overload
def apply_processor(name: ProcessorName, value: object, args: list[str] | None = None) -> object: ...


def apply_processor(name: ProcessorName, value: object, args: list[str] | None = None) -> object:
    """Apply a named processor to a value.

    Raises KeyError if the processor name is not registered.
    """
    processor_name = ProcessorName(name)
    if processor_name not in PROCESSOR_REGISTRY:
        raise KeyError(f"Unknown processor: {name!r}. Available: {list(PROCESSOR_REGISTRY.keys())}")
    func = PROCESSOR_REGISTRY[processor_name]
    if args:
        return func(value, *args)
    return func(value)
