(
    """Validators for primitive (non-nested) field values.

Factored out from validation logic so tests and code can reuse semantic checks.
"""
)

from typing import Any, List
from datetime import datetime

from ..models.parser_spec import FieldType
from ..models.validation import ValidationMismatch


def type_name(value: Any) -> str:
    if value is None:
        return "missing"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    return type(value).__name__


def _validate_text(name_path: str, value: Any) -> List[ValidationMismatch]:
    mismatches: List[ValidationMismatch] = []
    if not isinstance(value, str):
        mismatches.append(
            ValidationMismatch(
                field=name_path,
                expected_type="text",
                actual_type=type_name(value),
                message=f"Field '{name_path}' expected text, got {type_name(value)}",
            )
        )
    return mismatches


def _validate_link(name_path: str, value: Any) -> List[ValidationMismatch]:
    mismatches: List[ValidationMismatch] = []
    if not isinstance(value, str):
        mismatches.append(
            ValidationMismatch(
                field=name_path,
                expected_type="link",
                actual_type=type_name(value),
                message=f"Field '{name_path}' expected link string, got {type_name(value)}",
            )
        )
        return mismatches
    if not (value.startswith("http://") or value.startswith("https://") or value.startswith("/")):
        mismatches.append(
            ValidationMismatch(
                field=name_path,
                expected_type="link",
                actual_type="string",
                message=f"Field '{name_path}' does not look like a link: '{value}'",
            )
        )
    return mismatches


def _validate_number(name_path: str, value: Any) -> List[ValidationMismatch]:
    mismatches: List[ValidationMismatch] = []
    if not isinstance(value, (int, float)):
        mismatches.append(
            ValidationMismatch(
                field=name_path,
                expected_type="number",
                actual_type=type_name(value),
                message=f"Field '{name_path}' expected number, got {type_name(value)}",
            )
        )
    return mismatches


def _validate_date(name_path: str, value: Any) -> List[ValidationMismatch]:
    mismatches: List[ValidationMismatch] = []
    if not isinstance(value, str):
        mismatches.append(
            ValidationMismatch(
                field=name_path,
                expected_type="date",
                actual_type=type_name(value),
                message=f"Field '{name_path}' expected date string, got {type_name(value)}",
            )
        )
        return mismatches
    try:
        datetime.fromisoformat(value)
    except Exception:  # pylint: disable=broad-except
        mismatches.append(
            ValidationMismatch(
                field=name_path,
                expected_type="date",
                actual_type="string",
                message=f"Field '{name_path}' is not a valid ISO date: '{value}'",
            )
        )
    return mismatches


def _validate_value(name_path: str, base_type: FieldType, value: Any) -> List[ValidationMismatch]:
    """Dispatch to the right validator for `base_type`.

    Returns list of `ValidationMismatch` (empty if valid).
    """
    if value is None:
        return [
            ValidationMismatch(
                field=name_path,
                expected_type=base_type.value,
                actual_type="missing",
                message=f"Field '{name_path}' is missing",
            )
        ]

    if base_type == FieldType.TEXT:
        return _validate_text(name_path, value)
    if base_type == FieldType.LINK:
        return _validate_link(name_path, value)
    if base_type == FieldType.NUMBER:
        return _validate_number(name_path, value)
    if base_type == FieldType.DATE:
        return _validate_date(name_path, value)

    # Fallback: treat as text
    return _validate_text(name_path, value)
