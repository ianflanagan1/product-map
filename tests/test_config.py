"""An app's .config/ianf-product-map.toml and .config/ianf-tracker.toml: what the app is called,
how to read it, where its map goes, and where problems with it are filed."""

import json
import subprocess
import tomllib
from pathlib import Path

import jsonschema
import pytest
from cli_kit.outcome import Precondition

from product_map import config

ROOT = Path(__file__).parent.parent
SCHEMA = ROOT / "schema" / "ianf-product-map.v1.json"
APP = 'version = 1\nname = "Shop"\nadapter = "dog-cafe"\n'
TRACKER = 'version = 1\nkind = "jira"\nsite = "shop.atlassian.net"\nspace = "SHOP"\n'
PLACES = 'source = "app"\nstatic = "static"\nout = "docs/map"\n'


def write(root: Path, app: str | None, tracker: str | None) -> Path:
    """Writes the app's files in a repository at root, leaving out any given as None, and returns
    its product-map file."""
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / ".config").mkdir(exist_ok=True)
    path = root / ".config" / "ianf-product-map.toml"
    for content, file in ((app, path), (tracker, root / ".config" / "ianf-tracker.toml")):
        if content is not None:
            file.write_text(content)
    return path


def problem(root: Path) -> list[str]:
    with pytest.raises(Precondition) as raised:
        config.load(root)
    return [raised.value.message, *raised.value.details]


def test_reads_the_app_s_settings_and_its_tracker_settings(tmp_path, capsys):
    write(tmp_path, APP + PLACES, TRACKER)
    settings = config.load(tmp_path)
    assert (settings.name, settings.adapter) == ("Shop", "dog-cafe")
    assert (settings.source, settings.static, settings.out) == (
        tmp_path / "app",
        tmp_path / "static",
        tmp_path / "docs/map",
    )
    assert settings.tracker == {
        "version": 1,
        "kind": "jira",
        "site": "shop.atlassian.net",
        "space": "SHOP",
    }
    assert capsys.readouterr().err == ""


def test_settings_left_out_take_their_defaults_and_say_so(tmp_path, capsys):
    path = write(tmp_path, APP, TRACKER)
    settings = config.load(tmp_path)
    assert (settings.source, settings.static, settings.out) == (
        tmp_path,
        None,
        tmp_path / "docs/product-map",
    )
    assert capsys.readouterr().err == (
        f"Using the defaults for source, static and out: {path} doesn't set them.\n"
    )


def test_an_app_without_a_product_map_file_is_named(tmp_path):
    write(tmp_path, None, TRACKER)
    assert problem(tmp_path) == [
        f"No {tmp_path}/.config/ianf-product-map.toml.",
        "Create one, as product-map's README shows.",
    ]


def test_a_product_map_file_without_a_version_is_named(tmp_path):
    path = write(tmp_path, APP.replace("version = 1\n", ""), TRACKER)
    assert problem(tmp_path)[0] == f"No version in {path}."


def test_without_a_tracker_file_there_is_no_map(tmp_path):
    write(tmp_path, APP, None)
    assert problem(tmp_path) == [
        f"No {tmp_path}/.config/ianf-tracker.toml.",
        "A map says where problems with the app are filed: add the file jira-tools reads.",
    ]


def test_a_tracker_version_product_map_doesnt_read_is_named(tmp_path):
    write(tmp_path, APP, TRACKER.replace("version = 1", "version = 2"))
    tracker = tmp_path / ".config" / "ianf-tracker.toml"
    assert problem(tmp_path)[0] == f"{tracker} is version 2, which this tool doesn't read."


@pytest.mark.parametrize("missing", ["site", "space"])
def test_the_tracker_needs_a_site_and_space(tmp_path, missing):
    lines = [line for line in TRACKER.splitlines() if not line.startswith(missing)]
    write(tmp_path, APP, "\n".join(lines) + "\n")
    tracker = tmp_path / ".config" / "ianf-tracker.toml"
    assert problem(tmp_path) == [f"No {missing} set in {tracker}."]


@pytest.mark.parametrize("needed", ["name", "adapter"])
def test_the_app_s_name_and_adapter_are_needed(tmp_path, needed):
    lines = [line for line in APP.splitlines() if not line.startswith(needed)]
    path = write(tmp_path, "\n".join(lines) + "\n", TRACKER)
    assert problem(tmp_path) == [f"{needed} must be set in {path}."]


def test_an_unknown_setting_is_named(tmp_path):
    path = write(tmp_path, APP + 'report_to = "X"\n', TRACKER)
    assert problem(tmp_path) == [f"Unknown settings in {path}: report_to."]


def test_an_unknown_adapter_is_named(tmp_path):
    write(tmp_path, APP.replace("dog-cafe", "rails"), TRACKER)
    assert problem(tmp_path)[0] == "No adapter 'rails'."


def test_the_map_s_file_name_is_the_app_s_name_in_lower_case_joined_by_hyphens(tmp_path):
    write(tmp_path, APP.replace('"Shop"', '"Shop & Go 2"'), TRACKER)
    assert config.load(tmp_path).slug == "shop-go-2"


def test_the_schema_has_the_settings_product_map_reads():
    schema = json.loads(SCHEMA.read_text())
    assert set(schema["properties"]) == {"version", *config.SETTINGS}


def test_the_readme_s_example_names_the_schema_and_meets_it():
    readme = (ROOT / "README.md").read_text()
    example = "#:schema" + readme.split("```toml\n#:schema", 1)[1].split("```", 1)[0]
    schema = json.loads(SCHEMA.read_text())
    assert example.splitlines()[0] == f"#:schema {schema['$id']}"
    jsonschema.validate(tomllib.loads(example), schema)
