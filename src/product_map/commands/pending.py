"""product-map pending [<dir>]

Prints, as JSON, each page and action of the app in <dir>, the current folder by default, whose
description is missing or was written from facts that have since changed: its key and its facts.
Describe them with product-map describe.
"""

import json
from pathlib import Path

from cli_kit import cli
from cli_kit.outcome import NothingToDo

from product_map import config, descriptions, scan


def register(subparsers: cli.Subparsers) -> None:
    parser = subparsers.add_parser(
        "pending",
        help="list the pages and actions waiting for a description",
        description=__doc__.split("\n\n", 1)[1],
    )
    parser.add_argument("dir", nargs="?", default=".", help="the app's repository")
    parser.set_defaults(run=lambda args: pending(Path(args.dir)))


def pending(root: Path) -> NothingToDo:
    settings = config.load(root)
    waiting = descriptions.pending(scan.app(settings), descriptions.load(settings.out))
    if not waiting:
        return NothingToDo("Every page and action is described.")
    print(json.dumps([{"key": e.key, "facts": e.facts()} for e in waiting], indent=2))
    return NothingToDo(f"{len(waiting)} waiting for a description.")
