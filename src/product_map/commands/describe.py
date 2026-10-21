"""product-map describe [<dir>]

Keeps the descriptions given on stdin, for pages and actions waiting for one in the app in <dir>,
the current folder by default. Each starts with a `## ` line giving its key, as product-map pending
names it. An action's has a `Title: ` line next, naming what people do. The lines after are its
description:

    ## page:favs
    Your saved favourites, page by page. ...

    ## action:DELETE /account
    Title: Deleting your account
    Pressing Delete Account on the Account page ...

Each description is a few sentences of plain words, at most 500 characters. Nothing is kept unless
every one is right. Descriptions of pages and actions the app no longer has are dropped.
"""

import sys
from pathlib import Path
from typing import TextIO

from cli_kit import cli
from cli_kit.outcome import Done, Precondition

from product_map import config, descriptions, scan


def register(subparsers: cli.Subparsers) -> None:
    parser = subparsers.add_parser(
        "describe",
        help="keep the descriptions given on stdin",
        description=__doc__.split("\n\n", 1)[1],
    )
    parser.add_argument("dir", nargs="?", default=".", help="the app's repository")
    parser.set_defaults(run=lambda args: describe(Path(args.dir)))


def describe(root: Path, stdin: TextIO | None = None) -> Done:
    stdin = stdin or sys.stdin
    given = parse("" if stdin.isatty() else stdin.read())
    settings = config.load(root)
    kept = descriptions.accept(scan.app(settings), descriptions.load(settings.out), given)
    descriptions.save(settings.out, kept)
    return Done(f"Described {len(given)}.", str(settings.out / descriptions.FILE))


def parse(text: str) -> dict[str, dict]:
    """The descriptions in text, by key, each with its title if it has one."""
    given: dict[str, dict] = {}
    key: str | None = None
    lines: list[str] = []

    def end() -> None:
        if key is None:
            return
        record: dict = {}
        body = [line for line in lines]
        while body and not body[0].strip():
            body.pop(0)
        if body and body[0].startswith("Title:"):
            record["title"] = body.pop(0).removeprefix("Title:").strip()
        record["description"] = " ".join(" ".join(body).split())
        given[key] = record

    for line in text.splitlines():
        if line.startswith("## "):
            end()
            key, lines = line[3:].strip(), []
            if key in given:
                raise Precondition(f"{key} is described twice.")
        elif key is None:
            if line.strip():
                raise Precondition("Start each description with a ## line giving its key.")
        else:
            lines.append(line)
    end()
    if not given:
        raise Precondition("No descriptions given.", "Give them on stdin, each under a ## line.")
    return given
