"""Reading an app as its .workspace.toml says, and which version of it was read."""

from cli_kit import proc

from product_map.adapters import ADAPTERS
from product_map.config import Config
from product_map.facts import App


def app(settings: Config) -> App:
    return ADAPTERS[settings.adapter](settings.source, settings.static)


def version(settings: Config) -> str:
    """The version of the app read: its latest tag and commit, and the commit's date, or "its
    working copy" outside a git repository."""
    git = ("git", "-C", str(settings.root))
    if not proc.succeeds(*git, "rev-parse", "HEAD"):
        return "its working copy"
    described = proc.output(*git, "describe", "--tags", "--always")
    date = proc.output(*git, "log", "-1", "--format=%cs")
    return f"{described}, {date}"
