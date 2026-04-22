from __future__ import annotations

from pathlib import Path

import click
import yaml

from .engine import ParseEngine
from .models.output import EngineOutput
from .models.parser_spec import ParseSpec
from .models.validation import ExpectedResults, FileExpectedItems
from .validation.true_validate import validate_files


@click.group()
def cli() -> None:
    """Declarative scraper utilities."""


@cli.command()
@click.argument("spec_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("html_path", type=click.Path(exists=True, dir_okay=True, path_type=Path))
@click.option("--output", "output_path", type=click.Path(dir_okay=False, path_type=Path))
def parse(spec_path: Path, html_path: Path, output_path: Path | None) -> None:
    """Apply a spec to one or more HTML files."""

    spec = ParseSpec.from_yaml_file(spec_path)
    engine = ParseEngine(spec)
    results: dict[str, EngineOutput] = {}
    if html_path.is_file():
        html_files = [html_path]
    else:
        html_files = sorted(html_path.glob("*.html"))

    for html_file in html_files:
        html = html_file.read_text(encoding="utf-8")
        parsed = engine.parse(html)
        results[html_file.name] = parsed

    file_results = ExpectedResults(
        data_path=html_path if html_path.is_dir() else html_path.parent,
        files=[FileExpectedItems.from_engine_output(file_name, output) for file_name, output in results.items()],
    )

    if output_path is not None:
        file_results.to_yaml_file(output_path)
        click.echo(f"Wrote parsed results to {output_path}")
        return

    rendered_yaml = yaml.safe_dump(file_results.model_dump(), sort_keys=False, allow_unicode=True)
    click.echo(rendered_yaml, nl=False)


@cli.command()
@click.argument("spec_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("expected_results_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--field-path", "-f", type=str, help="Optional dot path to a specific field to validate (e.g. 'items.name')."
)
def validate(spec_path: Path, expected_results_path: Path, field_path: str | None) -> None:
    """Validate a spec against YAML expected extraction results."""

    validation_result = validate_files(
        expected_values_path=expected_results_path,
        spec_file_path=spec_path,
        field_path=field_path,
    )
    if validation_result.passed:
        click.echo(
            f"Validation passed for {validation_result.total_files} file(s) and {validation_result.total_items} extracted field(s)."
        )
        return

    for file_result in validation_result.file_results:
        if file_result.passed:
            continue
        click.echo(f"{file_result.file_name}:")
        for error in file_result.errors:
            click.echo(f"  - {error}")

    raise click.ClickException(
        f"Validation failed for {validation_result.failures} of {validation_result.total_files} file(s)."
    )
