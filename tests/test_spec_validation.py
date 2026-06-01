from spextract.models.parser_spec import FieldSpec, FieldType, ParseSpec
from spextract.validation.spec_validate import validate_spec_output


def test_validate_spec_output_simple():
    spec = ParseSpec(
        name="TestSpec",
        fields={
            "title": FieldSpec(
                selector=".title",
                type=FieldType.TEXT,
                required=True,
            )
        },
    )
    data = {"title": "Hello World"}
    result = validate_spec_output(spec, data)
    assert result.is_valid


def test_validate_spec_output_nested_multiple():
    spec = ParseSpec(
        name="TestNestedMultiple",
        fields={
            "authors": FieldSpec(
                selector=".author",
                type=FieldType.OBJECT,
                required=True,
                multiple=True,
                fields={
                    "name": FieldSpec(
                        selector=".name",
                        type=FieldType.TEXT,
                        required=True,
                    ),
                    "age": FieldSpec(
                        selector=".age",
                        type=FieldType.NUMBER,
                        required=False,
                    ),
                },
            )
        },
    )
    data = {
        "authors": [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
    }
    result = validate_spec_output(spec, data)
    assert result.is_valid


def test_validate_spec_output_nested_single():
    spec = ParseSpec(
        name="TestNestedSingle",
        fields={
            "publisher": FieldSpec(
                selector=".publisher",
                type=FieldType.OBJECT,
                required=True,
                multiple=False,
                fields={
                    "name": FieldSpec(
                        selector=".name",
                        type=FieldType.TEXT,
                        required=True,
                    ),
                    "location": FieldSpec(
                        selector=".location",
                        type=FieldType.TEXT,
                        required=False,
                    ),
                },
            )
        },
    )
    data = {"publisher": {"name": "Acme Publishing", "location": "NYC"}}
    result = validate_spec_output(spec, data)
    assert result.is_valid


def test_validate_spec_output_required_field_missing():
    spec = ParseSpec(
        name="TestRequiredMissing",
        fields={
            "title": FieldSpec(
                selector=".title",
                type=FieldType.TEXT,
                required=True,
            )
        },
    )
    data = {}
    result = validate_spec_output(spec, data)
    assert not result.is_valid
    assert any(m.field == "title" and m.actual_type == "missing" for m in result.mismatches)


def test_validate_spec_output_malformatted_url():
    spec = ParseSpec(
        name="TestMalformedUrl",
        fields={
            "website": FieldSpec(
                selector=".website",
                type=FieldType.LINK,
                required=True,
            )
        },
    )
    data = {"website": "not_a_url"}
    result = validate_spec_output(spec, data)
    assert not result.is_valid
    assert any("does not look like a link" in m.message for m in result.mismatches)


def test_validate_spec_output_missing_string():
    spec = ParseSpec(
        name="TestMissingString",
        fields={
            "title": FieldSpec(
                selector=".title",
                type=FieldType.TEXT,
                required=True,
            )
        },
    )
    data = {}  # missing 'title'
    result = validate_spec_output(spec, data)
    assert not result.is_valid
    assert any("missing" in m.actual_type for m in result.mismatches)


def test_validate_spec_output_single_instead_of_multiple():
    spec = ParseSpec(
        name="TestSingleInsteadOfMultiple",
        fields={
            "tags": FieldSpec(
                selector=".tag",
                type=FieldType.TEXT,
                required=True,
                multiple=True,
            )
        },
    )
    data = {"tags": "not_a_list"}
    result = validate_spec_output(spec, data)
    assert not result.is_valid
    assert any("expected list" in m.message for m in result.mismatches)
