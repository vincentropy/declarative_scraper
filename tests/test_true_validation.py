# pylint: disable=protected-access
from pathlib import Path

import pytest

from py_decs.models.parser_spec import FieldSpec, FieldType, ParseSpec
from py_decs.models.validation import FileExpectedItems
from py_decs.validation.true_validate import _compare_values, validate_files, validate_spec_against_data


class TestCompareValues:
    def test_matching_string_produces_no_errors(self) -> None:
        errors: list[str] = []
        _compare_values("hello", "hello", "field", errors)
        assert not errors

    def test_mismatched_string_appends_error(self) -> None:
        errors: list[str] = []
        _compare_values("actual", "expected", "field", errors)
        assert len(errors) == 1
        assert "field" in errors[0]

    def test_empty_string_expected_and_none_actual_is_ok(self) -> None:
        errors: list[str] = []
        _compare_values(None, "", "field", errors)
        assert not errors

    def test_matching_dict_produces_no_errors(self) -> None:
        errors: list[str] = []
        _compare_values({"a": "1"}, {"a": "1"}, "root", errors)
        assert not errors

    def test_non_dict_against_dict_expected_appends_error(self) -> None:
        errors: list[str] = []
        _compare_values("not_a_dict", {"a": "1"}, "root", errors)
        assert errors

    def test_matching_list_produces_no_errors(self) -> None:
        errors: list[str] = []
        _compare_values(["a", "b"], ["a", "b"], "root", errors)
        assert not errors

    def test_list_length_mismatch_appends_error(self) -> None:
        errors: list[str] = []
        _compare_values(["a"], ["a", "b"], "root", errors)
        assert errors

    def test_target_field_path_suppresses_unrelated_errors(self) -> None:
        errors: list[str] = []
        _compare_values("wrong", "right", "other_field", errors, target_field_path="target_field")
        assert not errors

    def test_target_field_path_allows_errors_on_matching_path(self) -> None:
        errors: list[str] = []
        _compare_values("wrong", "right", "target_field", errors, target_field_path="target_field")
        assert errors


class TestValidateSpecAgainstData:
    def _simple_spec(self) -> ParseSpec:
        return ParseSpec(
            name="test",
            fields={"title": FieldSpec(selector="h1::text", type=FieldType.TEXT)},
        )

    def test_returns_error_when_no_items_extracted(self) -> None:
        spec = self._simple_spec()
        result = validate_spec_against_data(spec, "<p>No heading here</p>")
        assert not result.passed
        assert result.errors

    def test_parses_html_string_and_returns_result(self) -> None:
        spec = self._simple_spec()
        result = validate_spec_against_data(spec, "<h1>Hello</h1>")
        assert result.item_count == 1

    def test_compares_against_expected_values(self) -> None:
        spec = self._simple_spec()
        result = validate_spec_against_data(spec, "<h1>Hello</h1>", expected={"title": "Hello"})
        assert result.passed

    def test_reports_mismatch_against_expected_values(self) -> None:
        spec = self._simple_spec()
        result = validate_spec_against_data(spec, "<h1>Actual</h1>", expected={"title": "Expected"})
        assert not result.passed

    def test_raises_for_invalid_field_path(self) -> None:
        spec = self._simple_spec()
        with pytest.raises(ValueError, match="does not exist"):
            validate_spec_against_data(spec, "<h1>Hi</h1>", field_path="nonexistent")

    def test_strips_fields_prefix_from_field_path(self) -> None:
        spec = self._simple_spec()
        # Should not raise — "fields.title" should resolve to "title"
        result = validate_spec_against_data(spec, "<h1>Hi</h1>", field_path="fields.title")
        assert result.item_count == 1


class TestValidateSpecAgainstDataNestedXpath:
    NESTED_HTML = """
<html>
  <body>
    <div class="item">
      <span class="name">Alpha</span>
      <span class="price">$10</span>
    </div>
    <div class="item">
      <span class="name">Beta</span>
      <span class="price">$20</span>
    </div>
  </body>
</html>
"""

    def _nested_spec(self) -> ParseSpec:
        return ParseSpec(
            name="test",
            fields={
                "items": FieldSpec(
                    selector="//div[@class='item']",
                    multiple=True,
                    fields={
                        "name": FieldSpec(selector=".//span[@class='name']/text()"),
                        "price": FieldSpec(selector=".//span[@class='price']/text()"),
                    },
                )
            },
        )

    def test_extracts_nested_fields(self) -> None:
        result = validate_spec_against_data(self._nested_spec(), self.NESTED_HTML)
        assert result.passed
        assert result.item_count == 1  # top-level dict counts as 1 item

    def test_passes_when_expected_nested_values_match(self) -> None:
        expected = FileExpectedItems(
            file="page.html",
            items={
                "items": [
                    {"name": "Alpha", "price": "$10"},
                    {"name": "Beta", "price": "$20"},
                ]
            },
        )
        result = validate_spec_against_data(self._nested_spec(), self.NESTED_HTML, expected=expected.items)
        assert result.passed

    def test_reports_error_on_nested_field_mismatch(self) -> None:
        expected = FileExpectedItems(
            file="page.html",
            items={
                "items": [
                    {"name": "Alpha", "price": "$99"},
                    {"name": "Beta", "price": "$20"},
                ]
            },
        )
        result = validate_spec_against_data(self._nested_spec(), self.NESTED_HTML, expected=expected.items)
        assert not result.passed
        assert any("price" in e for e in result.errors)

    def test_reports_error_on_wrong_item_count(self) -> None:
        expected = FileExpectedItems(
            file="page.html",
            items={"items": [{"name": "Alpha", "price": "$10"}]},
        )
        result = validate_spec_against_data(self._nested_spec(), self.NESTED_HTML, expected=expected.items)
        assert not result.passed

    def test_field_path_targets_nested_child(self) -> None:
        # Only the "name" sub-field is validated; price mismatch should be suppressed
        expected = FileExpectedItems(
            file="page.html",
            items={
                "items": [
                    {"name": "Alpha", "price": "$99"},
                    {"name": "Beta", "price": "$20"},
                ]
            },
        )
        result = validate_spec_against_data(
            self._nested_spec(), self.NESTED_HTML, expected=expected.items, field_path="items.name"
        )
        assert result.passed

    def test_field_path_finds_error_for_target_nested_child(self) -> None:
        # Only the "name" sub-field is validated; price mismatch should be suppressed
        expected = FileExpectedItems(
            file="page.html",
            items={
                "items": [
                    {"name": "Alpha", "price": "$99"},
                    {"name": "Wrong", "price": "$20"},
                ]
            },
        )
        result = validate_spec_against_data(
            self._nested_spec(), self.NESTED_HTML, expected=expected.items, field_path="items.name"
        )
        assert not result.passed

    def test_raises_for_invalid_nested_field_path(self) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            validate_spec_against_data(self._nested_spec(), self.NESTED_HTML, field_path="items.nonexistent")

    def test_field_path_without_index_validates_subfield_in_all_list_items(self) -> None:
        """items.name (no index) should check 'name' in every item in the list.
        A mismatch in 'name' for any item should be reported; 'price' mismatches
        should be suppressed."""
        expected = FileExpectedItems(
            file="page.html",
            items={
                "items": [
                    {"name": "WRONG", "price": "$99"},  # name wrong, price wrong
                    {"name": "Beta", "price": "$99"},  # name correct, price wrong
                ]
            },
        )
        result = validate_spec_against_data(
            self._nested_spec(), self.NESTED_HTML, expected=expected.items, field_path="items.name"
        )
        # Only the first item's name mismatch should be reported
        assert not result.passed
        assert any("name" in e for e in result.errors)
        # Price mismatches must be suppressed
        assert not any("price" in e for e in result.errors)

    def test_field_path_with_index_validates_subfield_only_in_that_item(self) -> None:
        """items.0.name should check 'name' only for the first list item.
        A name mismatch in the second item must be suppressed."""

        expected = FileExpectedItems(
            file="page.html",
            items={
                "items": [
                    {"name": "Alpha", "price": "$99"},  # name correct, price wrong
                    {"name": "WRONG", "price": "$99"},  # name wrong, price wrong
                ]
            },
        )
        result = validate_spec_against_data(
            self._nested_spec(), self.NESTED_HTML, expected=expected.items, field_path="items[0].name"
        )
        # First item's name matches → no errors about items[0].name
        # Second item's name mismatch must be suppressed (outside the focused index)
        assert result.passed


class TestValidateSpecAgainstDataDoublyNested:
    HTML = """
<html><body>
  <div class="item">
    <span class="name">Alpha</span>
    <div class="meta">
      <span class="color">red</span>
      <span class="size">L</span>
    </div>
  </div>
  <div class="item">
    <span class="name">Beta</span>
    <div class="meta">
      <span class="color">blue</span>
      <span class="size">M</span>
    </div>
  </div>
</body></html>
"""

    HTML_SINGLE_ITEM = """
<html><body>
  <div class="item">
    <span class="name">Alpha</span>
    <div class="meta">
      <span class="color">red</span>
      <span class="size">L</span>
    </div>
  </div>
</body></html>
"""

    def _spec(self) -> ParseSpec:
        return ParseSpec(
            name="test",
            fields={
                "items": FieldSpec(
                    selector="//div[@class='item']",
                    multiple=True,
                    fields={
                        "name": FieldSpec(selector=".//span[@class='name']/text()"),
                        "meta": FieldSpec(
                            selector=".//div[@class='meta']",
                            fields={
                                "color": FieldSpec(selector=".//span[@class='color']/text()"),
                                "size": FieldSpec(selector=".//span[@class='size']/text()"),
                            },
                        ),
                    },
                )
            },
        )

    def test_doubly_nested_items_extracted_and_compared(self) -> None:
        """Each list item contains a sub-field that is itself a nested object."""
        expected = FileExpectedItems(
            file="page.html",
            items={
                "items": [
                    {"name": "Alpha", "meta": {"color": "red", "size": "L"}},
                    {"name": "Beta", "meta": {"color": "blue", "size": "M"}},
                ]
            },
        )
        result = validate_spec_against_data(self._spec(), self.HTML, expected=expected.items)
        assert result.passed

    def test_doubly_nested_items_reports_mismatch_in_inner_field(self) -> None:
        """A mismatch inside the doubly-nested object is detected and reported."""
        expected = FileExpectedItems(
            file="page.html",
            items={
                "items": [
                    {"name": "Alpha", "meta": {"color": "red", "size": "XL"}},  # size wrong
                ]
            },
        )
        result = validate_spec_against_data(self._spec(), self.HTML_SINGLE_ITEM, expected=expected.items)
        assert not result.passed
        assert any("size" in e for e in result.errors)

    def test_doubly_nested_items_reports_mismatch_with_target_field_path(self) -> None:
        """A mismatch inside the doubly-nested object is detected and reported."""
        expected = FileExpectedItems(
            file="page.html",
            items={
                "items": [
                    {"name": "Alpha", "meta": {"color": "red", "size": "L"}},
                    {"name": "Beta", "meta": {"color": "WRONG", "size": "M"}},
                ]
            },
        )
        result = validate_spec_against_data(self._spec(), self.HTML, expected=expected.items, field_path="items.meta")
        assert not result.passed

    def test_doubly_nested_items_reports_mismatch_len_with_target_field_path(self) -> None:
        """A mismatch inside the doubly-nested object is detected and reported."""
        expected = FileExpectedItems(
            file="page.html",
            items={
                "items": [
                    {"name": "Alpha", "meta": {"color": "red", "size": "L"}},
                    {"name": "Beta", "meta": {"color": "blue", "size": "M"}},
                ]
            },
        )
        result = validate_spec_against_data(
            self._spec(), self.HTML_SINGLE_ITEM, expected=expected.items, field_path="items.meta"
        )
        assert not result.passed


class TestValidateExpectedValues:
    def test_validates_from_yaml_files(self, tmp_path: Path) -> None:
        html_dir = tmp_path / "data"
        html_dir.mkdir()
        (html_dir / "page.html").write_text("<h1>Hi</h1>", encoding="utf-8")

        spec_yaml = tmp_path / "spec.yaml"
        spec_yaml.write_text(
            "name: test\nversion: 1\nfields:\n  title:\n    selector: h1::text\n    type: text\n",
            encoding="utf-8",
        )

        expected_yaml = tmp_path / "expected.yaml"
        expected_yaml.write_text(
            f"version: 1\ndata_path: {html_dir}\nfiles:\n  - file: page.html\n    items:\n      title: Hi\n",
            encoding="utf-8",
        )

        result = validate_files(expected_yaml, spec_yaml)
        assert result.passed

    def test_raises_when_no_data_path_provided(self, tmp_path: Path) -> None:
        spec_yaml = tmp_path / "spec.yaml"
        spec_yaml.write_text(
            "name: test\nversion: 1\nfields:\n  title:\n    selector: h1::text\n    type: text\n",
            encoding="utf-8",
        )

        expected_yaml = tmp_path / "expected.yaml"
        expected_yaml.write_text(
            "version: 1\nfiles: []\n",
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="Data path not specified"):
            validate_files(expected_yaml, spec_yaml)
