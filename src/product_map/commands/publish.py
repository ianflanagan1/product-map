"""product-map publish <maps> [<dir>]

Copies the product map of the app in <dir>, the current folder by default, into the folder of
installed maps <maps>, as a folder named for the app, replacing an older map of the app whole.
The report-problem skill reads that folder, ~/.claude/product-maps on each machine, each time it
runs, so the next report uses the new map. A folder that already has this map is left as it is.
"""

from pathlib import Path

from cli_kit import cli
from cli_kit.outcome import Done, NothingToDo, Precondition

from product_map import config
from product_map.commands.build import FOLDER, read, write


def register(subparsers: cli.Subparsers) -> None:
    parser = subparsers.add_parser(
        "publish",
        help="install the product map in a folder of maps",
        description=__doc__.split("\n\n", 1)[1],
    )
    parser.add_argument("maps", help="the folder of maps, such as ~/.claude/product-maps")
    parser.add_argument("dir", nargs="?", default=".", help="the app's repository")
    parser.set_defaults(run=lambda args: publish(Path(args.maps).expanduser(), Path(args.dir)))


def publish(maps: Path, root: Path) -> Done | NothingToDo:
    settings = config.load(root)
    files = read(settings.out / FOLDER)
    if "index.md" not in files:
        raise Precondition(f"No map in {settings.out / FOLDER}.", f"Run product-map build {root}.")
    target = maps / settings.slug
    # The single file earlier versions installed, which the folder replaces.
    old_file = maps / f"{settings.slug}.md"
    if read(target) == files and not old_file.exists():
        return NothingToDo(f"{maps} already has this map of {settings.name}.")
    write(target, files)
    old_file.unlink(missing_ok=True)
    return Done(f"Published the map of {settings.name}.", str(target / "index.md"))
