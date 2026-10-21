"""The [product-map] and [tracker] tables of an app's .workspace.toml: what the app is called, how
to read it, where its map goes, and where problems with it are filed."""

from pathlib import Path

import pytest
from cli_kit.outcome import Precondition

from product_map import config

APP = '[product-map]\nname = "Shop"\nadapter = "dog-cafe"\n'
TRACKER = '[tracker]\nkind = "jira"\nsite = "shop.atlassian.net"\nspace = "SHOP"\n'
PLACES = 'source = "app"\nstatic = "static"\nout = "docs/map"\n'


def write(root: Path, content: str) -> Path:
    path = root / ".workspace.toml"
    path.write_text(content)
    return path


def problem(root: Path) -> list[str]:
    with pytest.raises(Precondition) as raised:
        config.load(root)
    return [raised.value.message, *raised.value.details]


def test_reads_the_app_s_settings_and_its_tracker_table(tmp_path, capsys):
    write(tmp_path, APP + PLACES + "\n" + TRACKER)
    settings = config.load(tmp_path)
    assert (settings.name, settings.adapter) == ("Shop", "dog-cafe")
    assert (settings.source, settings.static, settings.out) == (
        tmp_path / "app",
        tmp_path / "static",
        tmp_path / "docs/map",
    )
    assert settings.tracker == {"kind": "jira", "site": "shop.atlassian.net", "space": "SHOP"}
    assert capsys.readouterr().err == ""


def test_settings_left_out_take_their_defaults_and_say_so(tmp_path, capsys):
    path = write(tmp_path, APP + "\n" + TRACKER)
    settings = config.load(tmp_path)
    assert (settings.source, settings.static, settings.out) == (
        tmp_path,
        None,
        tmp_path / "docs/product-map",
    )
    assert capsys.readouterr().err == (
        f"Using the defaults for source, static and out: {path} doesn't set them.\n"
    )


def test_an_app_without_a_workspace_file_is_named(tmp_path):
    assert problem(tmp_path) == [
        f"No .workspace.toml in {tmp_path}.",
        "Create one, as product-map's README shows.",
    ]


def test_a_workspace_file_without_a_product_map_table_is_named(tmp_path):
    path = write(tmp_path, TRACKER)
    assert problem(tmp_path) == [
        f"No [product-map] table in {path}.",
        "Add one, as product-map's README shows.",
    ]


def test_without_a_tracker_table_there_is_no_map(tmp_path):
    path = write(tmp_path, APP)
    assert problem(tmp_path) == [
        f"No [tracker] table in {path}.",
        "A map says where problems with the app are filed: add the table jira-tools reads.",
    ]


@pytest.mark.parametrize("missing", ["site", "space"])
def test_the_tracker_needs_a_site_and_space(tmp_path, missing):
    lines = [line for line in TRACKER.splitlines() if not line.startswith(missing)]
    path = write(tmp_path, APP + "\n".join(lines) + "\n")
    assert problem(tmp_path) == [f"No {missing} set in [tracker] in {path}."]


@pytest.mark.parametrize("needed", ["name", "adapter"])
def test_the_app_s_name_and_adapter_are_needed(tmp_path, needed):
    lines = [line for line in APP.splitlines() if not line.startswith(needed)]
    path = write(tmp_path, "\n".join(lines) + "\n" + TRACKER)
    assert problem(tmp_path) == [f"{needed} must be set in [product-map] in {path}."]


def test_an_unknown_setting_is_named(tmp_path):
    path = write(tmp_path, APP + 'report_to = "X"\n' + TRACKER)
    assert problem(tmp_path) == [f"Unknown settings in [product-map] in {path}: report_to."]


def test_an_unknown_adapter_is_named(tmp_path):
    write(tmp_path, APP.replace("dog-cafe", "rails") + TRACKER)
    assert problem(tmp_path)[0] == "No adapter 'rails'."


def test_the_map_s_file_name_is_the_app_s_name_in_lower_case_joined_by_hyphens(tmp_path):
    write(tmp_path, APP.replace('"Shop"', '"Shop & Go 2"') + TRACKER)
    assert config.load(tmp_path).slug == "shop-go-2"
