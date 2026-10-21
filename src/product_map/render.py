"""The product map as Markdown, for anyone describing a problem with the app, and for Claude
helping them: its pages, what's on them, who can use them, what people do and the messages they
can see, in the words its screens use. Nothing in it names the code."""

import json
import re
from dataclasses import dataclass, field

from product_map.facts import App, Entry

INTRO = (
    "What people can see and do in {name}, in the words its screens use, for anyone describing a"
    " problem with it. Built by product-map: build it again rather than editing it."
)

# The front matter's line naming the version built from, which alone may change while the map
# says the same.
BUILT_FROM = re.compile(r"^built_from = .*\n", re.MULTILINE)


def header(name: str, version: str, tracker: dict) -> str:
    """The map's front matter, in TOML between +++ lines, so a script can read which app it is,
    what it was built from and where problems with it are filed; then its title and what it's
    for."""
    matter = f"app = {_toml(name)}\nbuilt_from = {_toml(version)}\n\n" + _table("tracker", tracker)
    intro = INTRO.format(name=name)
    return f"+++\n{matter}+++\n\n# {name}\n\n{intro}\n\n"


def same(old: dict[str, str], new: dict[str, str]) -> bool:
    """Whether two maps, as files by path, say the same, whatever version each was built
    from."""
    return {path: BUILT_FROM.sub("", text) for path, text in old.items()} == {
        path: BUILT_FROM.sub("", text) for path, text in new.items()
    }


def _table(name: str, table: dict) -> str:
    """table as TOML under [name]: its values first, then its tables under [name.key]."""
    values = {key: value for key, value in table.items() if not isinstance(value, dict)}
    lines = [f"[{name}]", *(f"{key} = {_toml(value)}" for key, value in values.items())]
    text = "\n".join(lines) + "\n"
    for key, value in table.items():
        if isinstance(value, dict):
            text += "\n" + _table(f"{name}.{key}", value)
    return text


def _toml(value: object) -> str:
    """A TOML value for a string, number, boolean or list of them."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml(item) for item in value) + "]"
    return json.dumps(str(value), ensure_ascii=False)


@dataclass
class Area:
    """A part of the app as people find their way round it: the pages under one address, such
    as /billing/..., and the things people do there."""

    slug: str
    title: str
    pages: list[Entry] = field(default_factory=list)
    actions: list[Entry] = field(default_factory=list)


OTHER = Area("other", "Other pages and things people do")

# Parts of an address that say nothing of where in the app it is, such as /api/v1.
NOT_A_PLACE = re.compile(r"api|v\d+")


def files(
    app: App, descriptions: dict[str, dict], name: str, version: str, tracker: dict
) -> dict[str, str]:
    """The map, as its files by path: index.md, read first, with the front matter, what's on
    every page and what's in each area; a file in areas/ for each area, with its pages and the
    things people do there in full; and choices.md, the choices the app offers. So a large
    app's map is read a part at a time."""
    everywhere = _everywhere(app)
    index = header(name, version, tracker) + (everywhere + "\n" if everywhere else "")
    listing = [
        "## Areas",
        "",
        "Each area's pages, and the things people do there, are in its file in `areas/`, next to"
        " this one, with what's on each page and the messages it can show."
        + (" The choices the app offers are in `choices.md`." if _has_choices(app) else ""),
        "",
    ]
    parts = areas(app)
    listing += [_listed(area, descriptions) for area in parts]
    result = {"index.md": index + "\n".join(listing) + "\n"}
    for area in parts:
        result[f"areas/{area.slug}.md"] = _area(area, name, descriptions)
    if _has_choices(app):
        result["choices.md"] = _choices(app, name)
    return result


def areas(app: App) -> list[Area]:
    """The app's areas, in the order their first pages come: each page in the area of the first
    fixed part of its addresses, such as billing for /billing/invoices, or home for /; each
    action in the area its address is in, past any /api/v1; and in Other, the pages with no
    address and the actions with no area of their own."""
    found: dict[str, Area] = {}
    other = Area(OTHER.slug, OTHER.title)
    for page in app.pages:
        place = _place(page.paths)
        if place is None:
            other.pages.append(page)
            continue
        found.setdefault(place, Area(_slug(place), page.name)).pages.append(page)
    for action in app.actions:
        place = _place(action.paths)
        (found[place] if place in found else other).actions.append(action)
    return [*found.values(), *([other] if other.pages or other.actions else [])]


def _place(paths: list[str]) -> str | None:
    """The first fixed part of the first address that has one, past any /api/v1; home for /
    alone; None with no address."""
    if not paths:
        return None
    for path in paths:
        parts = [part for part in path.split("/") if part]
        while parts and NOT_A_PLACE.fullmatch(parts[0]):
            parts.pop(0)
        if parts and not parts[0].startswith(":"):
            return parts[0]
    return "home"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "home"


def _listed(area: Area, descriptions: dict[str, dict]) -> str:
    pages = ", ".join(
        page.name + (f" ({', '.join(f'`{address(p)}`' for p in page.paths)})" if page.paths else "")
        for page in area.pages
    )
    actions = ", ".join(_title(action, descriptions) for action in area.actions)
    contents = ". ".join(part for part in (pages, actions) if part)
    return f"- {area.title}, `areas/{area.slug}.md`: {contents}."


def _area(area: Area, name: str, descriptions: dict[str, dict]) -> str:
    parts = [f"# {area.title}, in {name}\n"]
    if area.pages:
        parts.append("## Pages\n")
        parts += [_entry(page.name, page, descriptions) for page in area.pages]
    if area.actions:
        parts.append("## Things people do\n")
        parts += [_entry(_title(a, descriptions), a, descriptions) for a in area.actions]
    return "\n".join(parts)


def _title(action: Entry, descriptions: dict[str, dict]) -> str:
    return descriptions.get(action.key, {}).get("title") or action.name


def _everywhere(app: App) -> str:
    lines = ["## On every page", ""]
    if app.navigation:
        lines.append("- Links: " + ", ".join(_link(label, href) for label, href in app.navigation))
    lines += [f"- {_control(control)}" for control in app.everywhere]
    lines += [f"- Can show: {_quoted(message)}" for message in app.messages]
    return "\n".join(lines) + "\n" if len(lines) > 2 else ""


def _entry(title: str, entry: Entry, descriptions: dict[str, dict]) -> str:
    where = ", ".join(f"`{address(path)}`" for path in entry.paths) or "No address of its own"
    who = "only people logged in" if entry.login else "anyone"
    lines = [f"### {title}", "", f"{where} · {who}", ""]
    if description := descriptions.get(entry.key, {}).get("description"):
        lines += [description, ""]
    facts: list[str] = []
    if entry.texts:
        facts.append("- Shows: " + ", ".join(_quoted(text) for text in entry.texts))
    facts += [f"- {_control(control)}" for control in entry.controls]
    if entry.links:
        facts.append("- Links: " + ", ".join(_link(label, href) for label, href in entry.links))
    facts += [f"- Can show: {_quoted(message)}" for message in entry.messages]
    if facts:
        lines += [*facts, ""]
    return "\n".join(lines)


def address(path: str) -> str:
    """A route as people see it: /venue/:venueReference as /venue/<venue reference>, and
    /:townStr as /<town>."""

    def words(match: re.Match[str]) -> str:
        name = re.sub(r"(?<=[a-z])Str$", "", match[1])
        return "<" + " ".join(re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", name)).lower() + ">"

    return re.sub(r":(\w+)", words, path)


def _has_choices(app: App) -> bool:
    return any(app.words.values())


def _choices(app: App, name: str) -> str:
    lines = [f"# Choices {name} offers", ""]
    lines += [f"- {kind}: {', '.join(choices)}" for kind, choices in app.words.items() if choices]
    return "\n".join(lines) + "\n"


def _control(control: str) -> str:
    kind, _, label = control.partition(": ")
    return f"{kind.capitalize()}: {_quoted(label)}"


def _link(label: str, href: str) -> str:
    return f"{_quoted(label)} (`{href}`)" if href else _quoted(label)


def _quoted(text: str) -> str:
    return f"“{text}”"
