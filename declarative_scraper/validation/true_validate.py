from pathlib import Path
from typing import cast

from declarative_scraper.engine import ParseEngine
from declarative_scraper.models.output import DataValue
from declarative_scraper.models.parser_spec import ParseSpec
from declarative_scraper.models.validation import ExpectedResults, FileValidationResult, TrueValidationResult


def _compare_values(
    actual: object,
    expected: DataValue,
    path: str,
    errors: list[str],
    target_field_path: str | None = None,
) -> None:
    """Recursively compare an actual parsed value against an expected value."""
    if isinstance(expected, str):
        if expected == "" and (actual is None or actual == ""):
            return  # Treat empty string and None as equivalent for convenience
        if actual != expected and (not target_field_path or path == target_field_path):
            errors.append(f"{path}: expected {expected!r}, got {actual!r}")
    elif isinstance(expected, dict):
        if not isinstance(actual, dict):
            if not target_field_path or path == target_field_path:
                errors.append(f"{path}: expected dict for target field, got {type(actual).__name__}: {actual!r}")
            return
        for key, exp_val in expected.items():
            actual_val = actual.get(key)
            _compare_values(actual_val, exp_val, f"{path}.{key}", errors, target_field_path)
    elif isinstance(expected, list):
        exp_list = cast(list[DataValue], expected)
        if not isinstance(actual, list):
            if not target_field_path or path == target_field_path:
                errors.append(f"{path}: expected list, got {type(actual).__name__}: {actual!r}")
            return
        if len(actual) != len(expected):
            if not target_field_path or path == target_field_path:
                errors.append(f"{path}: expected {len(expected)} items, got {len(actual)}")
            return
        for i, (act_item, exp_item) in enumerate(zip(actual, exp_list)):
            _compare_values(act_item, exp_item, f"{path}[{i}]", errors, target_field_path)
    elif actual != expected and (not target_field_path or path == target_field_path):
        errors.append(f"{path}: expected {expected!r}, got {actual!r}")


def validate_spec_against_data(
    spec: ParseSpec,
    html: str,
    expected: dict[str, DataValue] | None = None,
    field_path: str | None = None,
) -> FileValidationResult:
    """Validate a parser spec against an HTML string.

    Parses the HTML using the spec and optionally compares against expected results.
    """
    engine = ParseEngine(spec)

    # if field_path starts with "fields.", remove that prefix for easier matching
    if field_path and field_path.startswith("fields."):
        field_path = field_path[len("fields.") :]
    if field_path is not None:
        # Support dot notation for nested fields
        field_parts = field_path.split(".")
        current = spec.fields
        for part in field_parts:
            if isinstance(current, dict) and part in current:
                nested_fields = current[part].fields
                current = nested_fields if nested_fields is not None else {}
            else:
                raise ValueError(f"Field path '{field_path}' does not exist in the spec.")

    items = engine.parse(html).data
    errors: list[str] = []

    if not items:
        errors.append("No items extracted")

    if expected:
        actual = items if items else {}
        for key, exp_val in expected.items():
            actual_val = actual.get(key)
            _compare_values(actual_val, exp_val, key, errors, field_path)

    return FileValidationResult(file_name="", item_count=len(items), errors=errors)


def validate_files(
    expected_values_path: Path,
    spec_file_path: Path,
    data_dir: Path | None = None,
    field_path: str | None = None,
) -> TrueValidationResult:
    """Validate an item directory containing parser_spec.yaml and expected.yaml.

    Args:
        expected_values_path: Path to the expected values YAML file.
        spec_file_path: Path to the parser spec YAML file.
        data_dir: Override for the data directory. Defaults to item_dir/../data.
        field_path: Optional dot path to a specific field to validate.
    """
    expected_values = ExpectedResults.from_yaml_file(expected_values_path)
    spec = ParseSpec.from_yaml_file(spec_file_path)

    if data_dir is None:
        data_dir = expected_values.data_path

    if data_dir is None:
        raise ValueError(
            "Data path not specified. Either include 'data_path' in the expected values YAML or provide --data-dir."
        )

    if not data_dir.is_absolute():
        data_dir = expected_values_path.parent / data_dir

    expected_by_file: dict[str, dict[str, DataValue]] = {fe.file: fe.items for fe in expected_values.files}

    html_files = sorted(data_dir.glob("*.html"))
    result = TrueValidationResult()

    if not html_files:
        result.file_results.append(
            FileValidationResult(
                file_name=str(data_dir),
                item_count=0,
                errors=[f"No HTML files found in {data_dir}"],
            )
        )
        return result

    for html_file in html_files:
        html = html_file.read_text(encoding="utf-8")
        file_expected = expected_by_file.get(html_file.name)
        file_result = validate_spec_against_data(spec, html, file_expected, field_path=field_path)
        result.file_results.append(
            FileValidationResult(
                file_name=html_file.name,
                item_count=file_result.item_count,
                errors=file_result.errors,
            )
        )

    return result
