from pathlib import Path

import yaml
from click.testing import CliRunner

from spextract.cli import cli

EXAMPLE_SPEC_PATH = Path(__file__).parent / "example_data" / "example_spec.yaml"
EXAMPLE_CITIES_HTML_PATH = Path(__file__).parent / "example_data" / "example_cities.html"


def test_parse_command_cities_page_title_and_first_city_population() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["parse", str(EXAMPLE_SPEC_PATH), str(EXAMPLE_CITIES_HTML_PATH)])
    print(result.output)

    assert result.exit_code == 0
    payload = yaml.safe_load(result.output)
    items = payload["files"][0]["items"]
    assert items["page_title"] == "World Cities"
    assert items["cities"][0]["population"] == "13960000"
