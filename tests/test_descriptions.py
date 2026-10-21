"""Descriptions written once and kept while what they describe stays the same."""

import pytest
from cli_kit.outcome import Precondition

from product_map import descriptions
from product_map.facts import App, Entry


def app(*entries: Entry) -> App:
    return App(
        pages=[e for e in entries if e.kind == "page"],
        actions=[e for e in entries if e.kind == "action"],
    )


PAGE = Entry("page", "home", "Home", ["/"], texts=["Welcome"])
ACTION = Entry("action", "POST /note", "POST /note", ["/note"])


def test_every_entry_waits_until_described():
    assert descriptions.pending(app(PAGE, ACTION), {}) == [PAGE, ACTION]


def test_a_description_is_kept_while_its_facts_stay_the_same():
    kept = descriptions.accept(app(PAGE), {}, {"page:home": {"description": " The  start. "}})
    assert kept == {"page:home": {"fingerprint": PAGE.fingerprint(), "description": "The start."}}
    assert descriptions.pending(app(PAGE), kept) == []


def test_a_change_to_its_facts_makes_it_wait_again():
    kept = descriptions.accept(app(PAGE), {}, {"page:home": {"description": "The start."}})
    changed = Entry("page", "home", "Home", ["/"], texts=["Welcome back"])
    assert descriptions.pending(app(changed), kept) == [changed]


def test_an_action_needs_a_title():
    with pytest.raises(Precondition) as raised:
        descriptions.accept(app(ACTION), {}, {"action:POST /note": {"description": "Saves."}})
    assert raised.value.details == ("action:POST /note: no title",)


@pytest.mark.parametrize(
    "given, problem",
    [
        ({"page:nope": {"description": "x"}}, "page:nope: not waiting for a description"),
        ({"page:home": {"description": " "}}, "page:home: no description"),
        ({"page:home": {"description": "x" * 501}}, "page:home: description over 500 characters"),
    ],
)
def test_a_wrong_description_keeps_nothing(given, problem):
    with pytest.raises(Precondition) as raised:
        descriptions.accept(app(PAGE), {}, given)
    assert problem in raised.value.details


def test_descriptions_of_entries_gone_from_the_app_are_dropped():
    old = {"page:gone": {"fingerprint": "x", "description": "Old."}}
    kept = descriptions.accept(app(PAGE), old, {"page:home": {"description": "New."}})
    assert list(kept) == ["page:home"]


def test_they_are_saved_and_loaded_back(tmp_path):
    kept = {"page:home": {"fingerprint": "f", "description": "Café."}}
    descriptions.save(tmp_path / "out", kept)
    assert descriptions.load(tmp_path / "out") == kept
    assert "Café" in (tmp_path / "out" / descriptions.FILE).read_text()
