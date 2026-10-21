"""An app's .workspace.toml, committed at its repository's root: in [product-map], what the app is
called, how to read it and where its map goes; in [tracker], where problems with it are filed,
which the map carries in its front matter, so a report is filed where the team's own issues are.

[product-map]
name = "Shop"               # what people call the app
adapter = "dog-cafe"        # how its code is laid out: see adapters/
source = "app"              # its code, from the repository's root; "." by default
static = "static"           # its public scripts, if any; none by default
out = "docs/product-map"    # where the map and its descriptions are kept; this by default

[tracker]                   # as jira-tools reads it: site and space are needed
kind = "jira"
site = "your-site.atlassian.net"
space = "PROJ"
"""

import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from cli_kit.outcome import Precondition

from product_map.adapters import ADAPTERS

FILE = ".workspace.toml"
SETTINGS = ("name", "adapter", "source", "static", "out")
WITH_DEFAULTS = ("source", "static", "out")


@dataclass(frozen=True)
class Config:
    root: Path
    name: str
    adapter: str
    source: Path
    static: Path | None
    out: Path
    tracker: dict = field(default_factory=dict)
    """The [tracker] table as it's written, for the map's front matter."""

    @property
    def slug(self) -> str:
        """The map's file name once installed: the name in lower case, words joined by -."""
        return re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-")


def load(root: Path) -> Config:
    path = root / FILE
    if not path.is_file():
        raise Precondition(f"No {FILE} in {root}.", "Create one, as product-map's README shows.")
    try:
        tables = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as error:
        raise Precondition(f"{path} isn't valid TOML.", str(error)) from None
    settings = tables.get("product-map")
    if not isinstance(settings, dict):
        raise Precondition(
            f"No [product-map] table in {path}.", "Add one, as product-map's README shows."
        )
    where = f"[product-map] in {path}"
    if unknown := settings.keys() - set(SETTINGS):
        raise Precondition(f"Unknown settings in {where}: {', '.join(sorted(unknown))}.")
    for needed in ("name", "adapter"):
        if not isinstance(settings.get(needed), str) or not settings[needed].strip():
            raise Precondition(f"{needed} must be set in {where}.")
    if settings["adapter"] not in ADAPTERS:
        known = ", ".join(sorted(ADAPTERS))
        raise Precondition(f"No adapter {settings['adapter']!r}.", f"Known adapters: {known}.")
    tracker = _tracker(tables.get("tracker"), path)
    if defaulted := [name for name in WITH_DEFAULTS if name not in settings]:
        names = " and ".join(", ".join(defaulted).rsplit(", ", 1))
        print(f"Using the defaults for {names}: {path} doesn't set them.", file=sys.stderr)
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


def _tracker(table: object, path: Path) -> dict:
    """The [tracker] table, which needs a site and space; the tracker's own tools check the
    rest."""
    if not isinstance(table, dict):
        raise Precondition(
            f"No [tracker] table in {path}.",
            "A map says where problems with the app are filed: add the table jira-tools reads.",
        )
    for needed in ("site", "space"):
        if not isinstance(table.get(needed), str) or not table[needed].strip():
            raise Precondition(f"No {needed} set in [tracker] in {path}.")
    return table
