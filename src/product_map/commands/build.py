"""product-map build [<dir>] [--check]

Writes the product map of the app in <dir>, the current folder by default, to map/ in the folder
its .config/ianf-product-map.toml names, once every page and action is described: index.md, a
file in areas/ for each area of the app, and choices.md. The map is left as it is while what it
says is unchanged, so building it after every commit changes it only when the app does. --check
writes nothing, and fails when the map is out of date.
"""

import shutil
from pathlib import Path

from cli_kit import cli
from cli_kit.outcome import Done, NothingToDo, Precondition

from product_map import config, descriptions, render, scan

FOLDER = "map"
# The single file earlier versions wrote the map to, removed when the map is built.
OLD_FILE = "product-map.md"


def register(subparsers: cli.Subparsers) -> None:
    parser = subparsers.add_parser(
        "build", help="write the product map", description=__doc__.split("\n\n", 1)[1]
    )
    parser.add_argument("dir", nargs="?", default=".", help="the app's repository")
    parser.add_argument("--check", action="store_true", help="only check it's up to date")
    parser.set_defaults(run=lambda args: build(Path(args.dir), check=args.check))


def build(root: Path, *, check: bool = False) -> Done | NothingToDo:
    settings = config.load(root)
    app = scan.app(settings)
    described = descriptions.load(settings.out)
    if waiting := descriptions.pending(app, described):
        raise Precondition(
            f"{len(waiting)} waiting for a description.",
            *(entry.key for entry in waiting),
            "Run the product-map skill, or give them with product-map describe.",
        )
    version = scan.version(settings)
    files = render.files(app, described, settings.name, version, settings.tracker)
    folder = settings.out / FOLDER
    old_file = settings.out / OLD_FILE
    if render.same(read(folder), files) and not old_file.exists():
        return NothingToDo("The product map is up to date.")
    if check:
        raise Precondition("The product map is out of date.", f"Run product-map build {root}.")
    write(folder, files)
    old_file.unlink(missing_ok=True)
    return Done("Built the product map.", str(folder / "index.md"))


def read(folder: Path) -> dict[str, str]:
    """The map in folder, as its files by path, or {} with none."""
    if not folder.is_dir():
        return {}
    return {path.relative_to(folder).as_posix(): path.read_text() for path in folder.rglob("*.md")}


def write(folder: Path, files: dict[str, str]) -> None:
    """Replaces the map in folder with files, so no file of an earlier map is left."""
    shutil.rmtree(folder, ignore_errors=True)
    for path, text in files.items():
        (folder / path).parent.mkdir(parents=True, exist_ok=True)
        (folder / path).write_text(text)
