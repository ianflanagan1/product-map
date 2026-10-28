"""pending, describe, build and publish, against the miniature app."""

import io
import json
import tomllib

import pytest
from cli_kit.outcome import Done, NothingToDo, Precondition

from product_map.__main__ import main
from product_map.commands.build import build
from product_map.commands.describe import describe, parse
from product_map.commands.pending import pending
from product_map.commands.publish import publish

MAP = "docs/product-map/map"


def front_matter(repo) -> dict:
    return tomllib.loads((repo / MAP / "index.md").read_text().split("+++\n")[1])


def waiting(repo, capsys) -> list[dict]:
    capsys.readouterr()
    pending(repo)
    out = capsys.readouterr().out
    return json.loads(out) if out else []


def describe_all(repo, capsys) -> None:
    sections = []
    for item in waiting(repo, capsys):
        title = "Title: Doing it\n" if item["key"].startswith("action:") else ""
        sections.append(f"## {item['key']}\n{title}About {item['key']}.\n")
    describe(repo, io.StringIO("\n".join(sections)))


def test_pending_lists_each_entry_with_its_facts(repo, capsys):
    keys = [item["key"] for item in waiting(repo, capsys)]
    assert keys == ["page:home", "page:note", "page:thanks", "action:POST /note"]


def test_build_waits_until_everything_is_described(repo):
    with pytest.raises(Precondition) as raised:
        build(repo)
    assert raised.value.message == "4 waiting for a description."
    assert not (repo / "docs").exists()


def test_build_writes_the_map_with_the_version_it_was_read_from(repo, capsys):
    describe_all(repo, capsys)
    result = build(repo)
    assert isinstance(result, Done)
    matter = front_matter(repo)
    assert matter["app"] == "Tiny Cafe"
    assert matter["built_from"] == "v1.2.0, 2026-10-01"
    assert "# Tiny Cafe\n" in (repo / MAP / "index.md").read_text()
    areas = "".join(path.read_text() for path in (repo / MAP / "areas").iterdir())
    assert "About page:home." in areas
    assert waiting(repo, capsys) == []


def test_a_build_with_nothing_new_to_say_leaves_the_map_alone(repo, capsys):
    describe_all(repo, capsys)
    build(repo)
    path = repo / MAP / "index.md"
    path.write_text(path.read_text().replace("v1.2.0", "v1.1.0"))
    assert isinstance(build(repo), NothingToDo)
    assert "v1.1.0" in path.read_text()


def test_the_map_says_where_problems_go_as_the_tracker_file_does(repo, capsys):
    describe_all(repo, capsys)
    build(repo)
    assert front_matter(repo)["tracker"] == {
        "version": 1,
        "kind": "jira",
        "site": "tiny.atlassian.net",
        "space": "TINY",
    }


def test_a_change_to_where_problems_go_builds_the_map_again(repo, capsys):
    describe_all(repo, capsys)
    build(repo)
    tracker = repo / ".config" / "ianf-tracker.toml"
    tracker.write_text(tracker.read_text().replace('"TINY"', '"CAFE"'))
    assert isinstance(build(repo, check=False), Done)
    assert front_matter(repo)["tracker"]["space"] == "CAFE"


def test_a_build_removes_the_files_of_areas_the_app_no_longer_has(repo, capsys):
    describe_all(repo, capsys)
    build(repo)
    stale = repo / MAP / "areas" / "gone.md"
    stale.write_text("# Gone\n")
    assert isinstance(build(repo), Done)
    assert not stale.exists()


def test_a_build_removes_the_single_file_map_of_earlier_versions(repo, capsys):
    describe_all(repo, capsys)
    old = repo / "docs/product-map/product-map.md"
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_text("# Tiny Cafe\n")
    build(repo)
    assert not old.exists()


def test_a_change_to_a_page_waits_for_its_description_again(repo, capsys):
    describe_all(repo, capsys)
    build(repo)
    body = repo / "app/resources/views/pages/thanks/body.php"
    body.write_text("<p>Thank you!</p>")
    assert [item["key"] for item in waiting(repo, capsys)] == ["page:thanks"]


def test_check_fails_only_when_the_map_is_out_of_date(repo, capsys):
    describe_all(repo, capsys)
    build(repo)
    assert isinstance(build(repo, check=True), NothingToDo)
    (repo / "app/resources/views/pages/home/body.php").write_text("<p>New</p>")
    describe_all(repo, capsys)
    with pytest.raises(Precondition) as raised:
        build(repo, check=True)
    assert raised.value.message == "The product map is out of date."


def test_describe_reads_each_section_s_key_title_and_description():
    text = """
## page:home
The start,
  over two lines.

## action:POST /note
Title:  Saving a note
Saves it. {"braces": "are fine"}
"""
    assert parse(text) == {
        "page:home": {"description": "The start, over two lines."},
        "action:POST /note": {
            "title": "Saving a note",
            "description": 'Saves it. {"braces": "are fine"}',
        },
    }


@pytest.mark.parametrize(
    "text, problem",
    [
        ("Loose words\n## page:home\nx", "Start each description with a ## line giving its key."),
        ("## page:home\nx\n## page:home\ny", "page:home is described twice."),
        ("  \n", "No descriptions given."),
    ],
)
def test_describe_refuses_what_it_cannot_read(repo, text, problem):
    with pytest.raises(Precondition) as raised:
        describe(repo, io.StringIO(text))
    assert raised.value.message == problem


def installed(maps) -> dict[str, str]:
    folder = maps / "tiny-cafe"
    return {str(p.relative_to(folder)): p.read_text() for p in folder.rglob("*.md")}


def built(repo) -> dict[str, str]:
    folder = repo / MAP
    return {str(p.relative_to(folder)): p.read_text() for p in folder.rglob("*.md")}


def test_publish_installs_the_map_in_a_folder_named_for_the_app(repo, maps, capsys):
    describe_all(repo, capsys)
    build(repo)
    result = publish(maps, repo)
    assert isinstance(result, Done)
    assert installed(maps) == built(repo)
    assert "index.md" in installed(maps)


def test_publish_does_nothing_when_the_folder_already_has_this_map(repo, maps, capsys):
    describe_all(repo, capsys)
    build(repo)
    publish(maps, repo)
    assert isinstance(publish(maps, repo), NothingToDo)


def test_publish_replaces_an_older_map_of_the_app_whole(repo, maps, capsys):
    describe_all(repo, capsys)
    build(repo)
    (maps / "tiny-cafe" / "areas").mkdir(parents=True)
    (maps / "tiny-cafe" / "areas" / "gone.md").write_text("# Gone\n")
    (maps / "tiny-cafe.md").write_text("# Tiny Cafe\n\nA single-file map.\n")
    assert isinstance(publish(maps, repo), Done)
    assert installed(maps) == built(repo)
    assert not (maps / "tiny-cafe.md").exists()


def test_publish_leaves_the_other_apps_maps_alone(repo, maps, capsys):
    describe_all(repo, capsys)
    build(repo)
    (maps / "dog-cafe").mkdir(parents=True)
    (maps / "dog-cafe" / "index.md").write_text("# Dog Cafe\n")
    publish(maps, repo)
    assert sorted(path.name for path in maps.iterdir()) == ["dog-cafe", "tiny-cafe"]
    assert (maps / "dog-cafe" / "index.md").read_text() == "# Dog Cafe\n"


def test_publish_needs_a_built_map(repo, maps):
    with pytest.raises(Precondition):
        publish(maps, repo)
    assert not maps.exists()


def test_an_app_without_a_product_map_file_is_named(repo):
    (repo / ".config" / "ianf-product-map.toml").unlink()
    with pytest.raises(Precondition) as raised:
        build(repo)
    assert raised.value.message == f"No {repo}/.config/ianf-product-map.toml."


def test_the_command_line_runs_each_command(repo, capsys):
    assert main(["pending", str(repo)]) == 0
    assert capsys.readouterr().out.endswith("➖ 4 waiting for a description.\n")
