from typing import Any, List

from ..models.output import DataValue
from ..models.parser_spec import FieldSpec, ParseSpec
from ..models.validation import ValidationMismatch, ValidationResult
from .validators import _validate_value, type_name




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
    # Delegate to nested or non-nested validators
    if field_spec.fields is not None:
        return _validate_nested(name_path, field_spec, value)
    return _validate_non_nested(name_path, field_spec, value)


def _validate_nested(name_path: str, field_spec: FieldSpec, value: Any) -> List[ValidationMismatch]:
    mismatches: List[ValidationMismatch] = []
    expected = _expectation_for_field(field_spec)
    actual = type_name(value)

    # Handle missing
    if value is None:
        if field_spec.required:
            mismatches.append(
                ValidationMismatch(
                    field=name_path,
                    expected_type=expected,
                    actual_type="missing",
                    message=f"Field '{name_path}' is required but missing",
                )
            )
        return mismatches

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


def _validate_non_nested(name_path: str, field_spec: FieldSpec, value: Any) -> List[ValidationMismatch]:
    mismatches: List[ValidationMismatch] = []
    expected = _expectation_for_field(field_spec)
    actual = type_name(value)

    # Handle missing
    if value is None:
        if field_spec.required:
            mismatches.append(
                ValidationMismatch(
                    field=name_path,
                    expected_type=expected,
                    actual_type="missing",
                    message=f"Field '{name_path}' is required but missing",
                )
            )
        return mismatches

    base_type = field_spec.type

    def _validate_single(item_value: Any, item_path: str) -> None:
        for vm in _validate_value(item_path, base_type, item_value):
            mismatches.append(vm)

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
            _validate_single(item, f"{name_path}[{idx}]")
        return mismatches

    # single value expected
    _validate_single(value, name_path)
    return mismatches


def validate_spec_output(spec: ParseSpec, data: dict[str, DataValue]) -> ValidationResult:
    """Validate that the engine output `data` matches the `spec`.

    Returns a `ValidationResult` containing any mismatches found.
    """
    mismatches: List[ValidationMismatch] = []

    for field_name, field_spec in spec.fields.items():
        if field_name not in data:
            if field_spec.required:
                mismatches.append(
                    ValidationMismatch(
                        field=field_name,
                        expected_type=_expectation_for_field(field_spec),
                        actual_type="missing",
                        message=f"Field '{field_name}' missing in output.",
                    )
                )
            continue
        value = data[field_name]
        mismatches.extend(_validate_field_recursive(field_name, field_spec, value))

    return ValidationResult(mismatches=mismatches)
