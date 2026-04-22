from pathlib import Path

import yaml
from click.testing import CliRunner

from py_decs.cli import cli


SPEC_YAML = """
name: article
version: 1
fields:
  title:
    selector: h1::text
    type: text
  price:
    selector: .price::text
    type: text
""".strip()


HTML = """
<html>
  <body>
    <h1>Example title</h1>
    <span class="price">$10</span>
  </body>
</html>
""".strip()


def test_parse_command_outputs_expected_results_yaml(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.yaml"
    html_path = tmp_path / "example.html"
    spec_path.write_text(SPEC_YAML, encoding="utf-8")
    html_path.write_text(HTML, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["parse", str(spec_path), str(html_path)])

    assert result.exit_code == 0
    payload = yaml.safe_load(result.output)
    assert payload["version"] == 1
    assert payload["data_path"] == str(tmp_path)
    assert payload["files"] == [
        {
            "file": "example.html",
            "items": {"title": "Example title", "price": "$10"},
        }
    ]


def test_validate_command_passes_for_matching_expected_results(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.yaml"
    html_path = tmp_path / "example.html"
    expected_path = tmp_path / "expected.yaml"
    spec_path.write_text(SPEC_YAML, encoding="utf-8")
    html_path.write_text(HTML, encoding="utf-8")
    expected_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "data_path": ".",
                "files": [
                    {
                        "file": "example.html",
                        "items": {"title": "Example title", "price": "$10"},
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", str(spec_path), str(expected_path)])

    assert result.exit_code == 0
    assert "Validation passed for 1 file(s)" in result.output


def test_validate_command_fails_for_mismatched_expected_results(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.yaml"
    html_path = tmp_path / "example.html"
    expected_path = tmp_path / "expected.yaml"
    spec_path.write_text(SPEC_YAML, encoding="utf-8")
    html_path.write_text(HTML, encoding="utf-8")
    expected_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "data_path": ".",
                "files": [
                    {
                        "file": "example.html",
                        "items": {"title": "Wrong title", "price": "$10"},
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", str(spec_path), str(expected_path)])

    assert result.exit_code != 0
    assert "expected 'Wrong title', got 'Example title'" in result.output
    assert "Validation failed for 1 of 1 file(s)." in result.output