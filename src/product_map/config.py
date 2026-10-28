"""An app's settings, committed in its repository's .config/ directory and read as they are in the
worktree given, so a branch can change them: in ianf-product-map.toml,
what the app is called, how to read it and where its map goes; in ianf-tracker.toml, where
problems with it are filed, which the map carries in its front matter, so a report is filed where
the team's own issues are.

    version = 1                 # the version of the file's format: see schema/
    name = "Shop"               # what people call the app
    adapter = "dog-cafe"        # how its code is laid out: see adapters/
    source = "app"              # its code, from the repository's root; "." by default
    static = "static"           # its public scripts, if any; none by default
    out = "docs/product-map"    # where the map and its descriptions are kept; this by default

ianf-tracker.toml is jira-tools' file: product-map needs its site and space, and copies the rest.
"""

import re
import sys
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import assert_never

import repo_settings
from cli_kit.outcome import Precondition
from repo_settings import Invalid, Missing, Settings, Source, Unlocatable, checkouts

from product_map.adapters import ADAPTERS

PURPOSE = "product-map"
TRACKER = "tracker"
SETTINGS = ("name", "adapter", "source", "static", "out")
WITH_DEFAULTS = ("source", "static", "out")


class Version(IntEnum):
    """The versions of ianf-product-map.toml's format product-map reads."""

    V1 = 1


class TrackerVersion(IntEnum):
    """The versions of jira-tools' ianf-tracker.toml product-map reads."""

    V1 = 1


@dataclass(frozen=True)
class Config:
    root: Path
    name: str
    adapter: str
    source: Path
    static: Path | None
    out: Path
    tracker: dict = field(default_factory=dict)
    """The app's tracker settings as they're written, with their version, for the map's front
    matter."""

    @property
    def slug(self) -> str:
        """The map's file name once installed: the name in lower case, words joined by -."""
        return re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-")


def load(directory: Path) -> Config:
    """The settings of the app whose repository directory is in, from the root of its worktree.
    Raises Precondition when they're missing or wrong."""
    root = checkouts.this_worktree(directory)
    if root is None:
        raise Precondition(f"{directory} isn't in a worktree of a git repository.")
    read = _read(root, PURPOSE, Version, "Create one, as product-map's README shows.")
    tracker = _tracker(root)
    match read.version:
        case Version.V1:
            return _config(root, read.table, read.where, tracker)
        case _:
            assert_never(read.version)


def _read[V: IntEnum](root: Path, purpose: str, versions: type[V], missing: str) -> Settings[V]:
    """The settings for purpose in the worktree at root. Raises Precondition, with missing as its
    advice when there's no file."""
    read = repo_settings.read(Source.LOCAL_THIS_WORKTREE, root, purpose, versions)
    match read:
        case Settings():
            return read
        case Missing():
            raise Precondition(f"No {read.where}.", missing)
        case Unlocatable() | Invalid():
            raise Precondition(read.message, *read.details)
        case _:
            assert_never(read)


def _config(root: Path, settings: dict, where: str, tracker: dict) -> Config:
    if unknown := settings.keys() - set(SETTINGS):
        raise Precondition(f"Unknown settings in {where}: {', '.join(sorted(unknown))}.")
    for needed in ("name", "adapter"):
        if not isinstance(settings.get(needed), str) or not settings[needed].strip():
            raise Precondition(f"{needed} must be set in {where}.")
    if settings["adapter"] not in ADAPTERS:
        known = ", ".join(sorted(ADAPTERS))
        raise Precondition(f"No adapter {settings['adapter']!r}.", f"Known adapters: {known}.")
    if defaulted := [name for name in WITH_DEFAULTS if name not in settings]:
        names = " and ".join(", ".join(defaulted).rsplit(", ", 1))
        print(f"Using the defaults for {names}: {where} doesn't set them.", file=sys.stderr)
    static = settings.get("static")
    return Config(
        root,
        settings["name"].strip(),
        settings["adapter"],
        root / settings.get("source", "."),
        root / static if static else None,
        root / settings.get("out", "docs/product-map"),
        tracker,
    )


def _tracker(root: Path) -> dict:
    """The app's tracker settings, with their version, for the map to carry: they need a site and
    space, and the tracker's own tools check the rest."""
    read = _read(
        root,
        TRACKER,
        TrackerVersion,
        "A map says where problems with the app are filed: add the file jira-tools reads.",
    )
    match read.version:
        case TrackerVersion.V1:
            for needed in ("site", "space"):
                value = read.table.get(needed)
                if not isinstance(value, str) or not value.strip():
                    raise Precondition(f"No {needed} set in {read.where}.")
        case _:
            assert_never(read.version)
    return {"version": read.version.value, **read.table}
