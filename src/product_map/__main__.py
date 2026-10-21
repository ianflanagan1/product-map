"""`product-map <command> ...`."""

import sys

from cli_kit import cli

from product_map.commands import build, describe, pending, publish

COMMANDS = [pending, describe, build, publish]


def main(argv: list[str] | None = None) -> int:
    return cli.run(
        "product-map",
        "Build a product map of an app, for the people who report problems with it.",
        COMMANDS,
        argv,
    )


if __name__ == "__main__":
    sys.exit(main())
