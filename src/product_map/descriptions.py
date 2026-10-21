"""The plain-words description of each page and action, written by Claude and kept in
descriptions.json beside the map with the fingerprint of the facts it was written from. While an
entry's facts don't change, its description is kept and nothing is asked of Claude."""

import json
from pathlib import Path

from cli_kit.outcome import Precondition

from product_map.facts import App, Entry

FILE = "descriptions.json"
LONGEST = 500


def load(out: Path) -> dict[str, dict]:
    path = out / FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise Precondition(f"{path} isn't valid JSON.", str(error)) from None


def save(out: Path, descriptions: dict[str, dict]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    text = json.dumps(descriptions, indent=2, sort_keys=True, ensure_ascii=False)
    (out / FILE).write_text(text + "\n")


def pending(app: App, descriptions: dict[str, dict]) -> list[Entry]:
    """The entries with no description, or one written from facts that have since changed."""
    return [
        entry
        for entry in app.entries()
        if descriptions.get(entry.key, {}).get("fingerprint") != entry.fingerprint()
    ]


def accept(app: App, descriptions: dict[str, dict], given: dict[str, dict]) -> dict[str, dict]:
    """descriptions with given's added: {key: {"description": ..., "title": ...}}, a title for
    each action. Raises Precondition, changing nothing, when any of given isn't right. Drops the
    descriptions of entries the app no longer has."""
    waiting = {entry.key: entry for entry in pending(app, descriptions)}
    problems: list[str] = []
    for key, value in given.items():
        entry = waiting.get(key)
        if entry is None:
            problems.append(f"{key}: not waiting for a description")
            continue
        text = " ".join(str(value.get("description", "")).split())
        title = " ".join(str(value.get("title", "")).split())
        if not text:
            problems.append(f"{key}: no description")
        elif len(text) > LONGEST:
            problems.append(f"{key}: description over {LONGEST} characters")
        if entry.kind == "action" and not title:
            problems.append(f"{key}: no title")
    if problems:
        raise Precondition("Some descriptions weren't accepted.", *problems)
    kept = {
        entry.key: descriptions[entry.key] for entry in app.entries() if entry.key in descriptions
    }
    for key, value in given.items():
        record = {"fingerprint": waiting[key].fingerprint()}
        record["description"] = " ".join(value["description"].split())
        if waiting[key].kind == "action":
            record["title"] = " ".join(value["title"].split())
        kept[key] = record
    return kept
