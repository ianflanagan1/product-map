"""The product-map skill: only the user starts it, and it may run what it needs without asking,
also headless, where no one is there to approve a command."""

import re
from fnmatch import fnmatchcase
from pathlib import Path

import pytest

SKILL = Path(__file__).parent.parent / "skills" / "product-map" / "SKILL.md"


def frontmatter() -> dict[str, str]:
    block = SKILL.read_text().split("---\n")[1]
    return dict(line.split(": ", 1) for line in block.splitlines())


def rules() -> list[str]:
    return re.findall(r"Bash\(([^)]*)\)", frontmatter()["allowed-tools"])


def allowed(command: str) -> bool:
    """Whether a Bash rule matches command, as Claude Code matches it: "*" matches anything,
    and a legacy "prefix:*" matches the prefix alone or followed by a space."""
    for rule in rules():
        globs = [rule[:-2], rule[:-2] + " *"] if rule.endswith(":*") else [rule]
        if any(fnmatchcase(command, glob) for glob in globs):
            return True
    return False


def loading_commands() -> list[str]:
    """What the skill runs as it loads, other than cat, which needs no rule, split at "; "."""
    lines = re.findall(r"^!`(.*)`$", SKILL.read_text(), re.MULTILINE)
    commands = [part for line in lines for part in line.replace(" 2>&1", "").split("; ")]
    return [c for c in commands if not c.startswith("cat ")]


def test_only_the_user_starts_it():
    assert frontmatter()["disable-model-invocation"] == "true"


def test_it_checks_product_map_is_installed_as_it_loads():
    assert "command -v product-map" in loading_commands()


@pytest.mark.parametrize("command", loading_commands())
def test_every_command_it_runs_as_it_loads_is_allowed(command):
    assert allowed(command)


@pytest.mark.parametrize(
    "command",
    [
        "product-map pending ~/projects/dog-cafe",
        "product-map describe . <<'EOF'\n## page:favs\nSaved.\nEOF",
        "product-map build .",
    ],
)
def test_the_commands_it_builds_with_are_allowed(command):
    assert allowed(command)


def test_it_may_read_the_code_but_not_change_it_or_publish():
    tools = [tool.strip() for tool in frontmatter()["allowed-tools"].split(",")]
    assert {"Read", "Grep", "Glob"} <= set(tools)
    assert not {"Write", "Edit"} & set(tools)
    assert not allowed("product-map publish ~/.claude/product-maps")
