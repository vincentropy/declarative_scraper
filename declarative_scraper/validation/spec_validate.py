"""
Validation logic for checking if engine output matches the declared spec."""

from typing import Any, List

from ..models.output import DataValue
from ..models.parser_spec import FieldSpec, ParseSpec
from ..models.validation import SpecValidationResult, ValidationMismatch
from .validators import validate_value, type_name


def _expectation_for_field(field_spec: FieldSpec) -> str:
    if field_spec.fields is not None:
        if field_spec.multiple:
            return "array<object>"
        return "object"
    base = field_spec.type.value
    if field_spec.multiple:
        return f"array<{base}>"
    return base


def _validate_field_recursive(name_path: str, field_spec: FieldSpec, value: Any) -> List[ValidationMismatch]:
    if field_spec.required and value is None:
        return [
            ValidationMismatch(
                field=name_path,
                expected_type=_expectation_for_field(field_spec),
                actual_type="missing",
                message=f"Field '{name_path}' missing in output.",
            )
        ]
    if value is None:
        # not required and missing is fine, no mismatches
        return []
    # Delegate to nested or non-nested validators
    if field_spec.fields is not None:
        return _validate_nested(name_path, field_spec, value)
    return _validate_non_nested(name_path, field_spec, value)


def _validate_nested(name_path: str, field_spec: FieldSpec, value: object) -> List[ValidationMismatch]:
    mismatches: List[ValidationMismatch] = []
    expected = _expectation_for_field(field_spec)
    actual = type_name(value)

    if field_spec.multiple:
        if not isinstance(value, list):
            mismatches.append(
                ValidationMismatch(
                    field=name_path,
                    expected_type=expected,
                    actual_type=actual,
                    message=f"Field '{name_path}' expected list of objects, got {actual}",
                )
            )
            return mismatches
        for idx, item in enumerate(value):
            if not isinstance(item, dict):
                mismatches.append(
                    ValidationMismatch(
                        field=f"{name_path}[{idx}]",
                        expected_type="object",
                        actual_type=type_name(item),
                        message=f"Expected object at '{name_path}[{idx}]', got {type_name(item)}",
                    )
                )
                continue
            assert field_spec.fields is not None  # for mypy - we know this is not None since we're in the nested case
            for child_name, child_spec in field_spec.fields.items():
                child_value = item.get(child_name)
                mismatches.extend(_validate_field_recursive(f"{name_path}.{child_name}", child_spec, child_value))
        return mismatches

    # single nested object expected
    if not isinstance(value, dict):
        mismatches.append(
            ValidationMismatch(
                field=name_path,
                expected_type=expected,
                actual_type=actual,
                message=f"Field '{name_path}' expected object, got {actual}",
            )
        )
        return mismatches

    assert field_spec.fields is not None  # for mypy - we know this is not None since we're in the nested case
    for child_name, child_spec in field_spec.fields.items():
        child_value = value.get(child_name)
        mismatches.extend(_validate_field_recursive(f"{name_path}.{child_name}", child_spec, child_value))
    return mismatches


def _validate_non_nested(name_path: str, field_spec: FieldSpec, value: object) -> List[ValidationMismatch]:
    mismatches: List[ValidationMismatch] = []
    expected = _expectation_for_field(field_spec)
    actual = type_name(value)
    base_type = field_spec.type

    if field_spec.multiple:
        if not isinstance(value, list):
            mismatches.append(
                ValidationMismatch(
                    field=name_path,
                    expected_type=expected,
                    actual_type=actual,
                    message=f"Field '{name_path}' expected list of {base_type.value}, got {actual}",
                )
            )
            return mismatches
        for idx, item in enumerate(value):
            val_result = validate_value(f"{name_path}[{idx}]", base_type, item)
            if val_result is not None:
                mismatches.append(val_result)
        return mismatches

    # single value expected
    val_result = validate_value(name_path, base_type, value)
    if val_result is not None:
        mismatches.append(val_result)
    return mismatches


def validate_spec_output(spec: ParseSpec, data: dict[str, DataValue], raise_: bool = False) -> SpecValidationResult:
    """Validate that the engine output `data` matches the `spec`.

    Returns a `SpecValidationResult` containing any mismatches found.
    """
    mismatches: List[ValidationMismatch] = []

    for field_name, field_spec in spec.fields.items():
        value = data[field_name] if field_name in data else None
        mismatches.extend(_validate_field_recursive(field_name, field_spec, value))

    result = SpecValidationResult(mismatches=mismatches)
    if raise_ and not result.is_valid:
        raise ValueError(f"Validation failed for output: {result}")
    return result
