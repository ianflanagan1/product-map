# product-map

A product map of an app: its pages, what's on each, who can use them, what people do there, the messages they can see and the choices it offers, in the words its screens use. It's what the [report-problem](https://github.com/ianflanagan1/claude-report-problem) skill reads to help colleagues describe a problem: it can offer them the app's real pages, buttons and messages as answers, and ask about what actually changes the app's behaviour, such as being logged in. Built on [cli-kit](../cli-kit).

Almost all of it is read from the code, the same every time. Claude writes only a few plain sentences for each page and action, and only when the facts read about it have changed since the last build.

```
$ product-map pending ~/projects/dog-cafe
[{"key": "page:favs", "facts": {...}}, ...]
➖ 2 waiting for a description.
$ product-map build ~/projects/dog-cafe
✅ Built the product map.
docs/product-map/map/index.md
```

## How it's built

1. **Read** (`adapters/`): the app's routes, which page each renders and whether it needs a login; each page's title, text, buttons, fields, tick boxes and links from its templates; the messages its scripts show; the messages its forms' checks fail with; and the choices in its enums. Code is read as text, never run.
2. **Describe** (Claude): each page and action gets a short description of what it's for and how people reach it, kept in `descriptions.json` with a fingerprint of the facts it was written from. While those facts don't change, nothing is asked of Claude again.
3. **Write** (`render.py`): the map as Markdown files in `map/`, below. What developers wrote in the code is shown to Claude to describe an entry but never written into the map. The map is rewritten only when what it says changes, so the version it names doesn't change on every commit.

## The map's files

A map is a folder, so Claude reads a large app's map a part at a time, as it reads a codebase: the index first, then only the areas a report is about, found by name or by searching for the words a colleague quotes.

| File | |
|---|---|
| `index.md` | the front matter, below; what's on every page; and each area, with its file, its pages and their addresses, and the things people do there |
| `areas/<area>.md` | an area's pages, each with its description, who can use it, what's on it, its links and the messages it can show; then the things people do there |
| `choices.md` | the choices the app offers, such as types and statuses |

An area is a part of the app as people find their way round it, read from its addresses: the pages under `/billing/...` are the area `billing`, named for its first page, and the things people do at `/billing/...` or `/api/v1/billing/...` go with them. Pages with no address, and things people do with no area of their own, are in `areas/other.md`.

## The app's .workspace.toml

Settings the app's team shares are in `.workspace.toml` at its repository's root. product-map reads two tables from it, and other tools read their own:

```toml
[product-map]
name = "Shop"               # needed: what people call the app
adapter = "dog-cafe"        # needed: how its code is laid out: see below
source = "app"              # its code, from the repository's root; "." if left out
static = "static"           # its public scripts, if any; none if left out
out = "docs/product-map"    # where the map and its descriptions are kept; this if left out

[tracker]                   # needed: where problems with the app are filed
kind = "jira"
site = "your-site.atlassian.net"
space = "PROJ"
```

`[tracker]` is the table jira-tools reads, so a colleague's report goes where the team's own issues do; see jira-tools' `workspace.example.toml` for the rest of it. Without it, or without its `site` and `space`, there's no map: a map that couldn't say where to file a problem would leave a colleague with a report and nowhere to send it. A setting left out of `[product-map]` takes its default, and the command says so.

Commit `out` with the app: the map and its descriptions are versioned and reviewed with the code they describe.

## The map's front matter

A map's `index.md` opens with TOML between `+++` lines, for scripts to read without reading the map: the report-problem skill's `maps.sh` reads the app's name and where to file from it, and `jira create --workspace <map>/index.md` files there.

```toml
+++
app = "Shop"
built_from = "v1.4.0-12-gabc1234, 2026-10-11"

[tracker]
kind = "jira"
site = "your-site.atlassian.net"
space = "PROJ"
+++
```

`[tracker]` is a copy of the `.workspace.toml` table, so a change to it builds the map again; `built_from` alone changing doesn't.

## Commands

| Command | |
|---|---|
| `product-map pending [<dir>]` | prints, as JSON, each page and action waiting for a description, with its facts |
| `product-map describe [<dir>]` | keeps the descriptions on stdin, each under a `## <key>` line, an action's with a `Title:` line |
| `product-map build [<dir>] [--check]` | writes the map once everything is described; `--check` writes nothing and fails when it's out of date |
| `product-map publish <maps> [<dir>]` | installs the map in a folder of maps, such as `~/.claude/product-maps`, as the folder `<name>/` |

`<dir>` is the app's repository, the current folder by default.

## The product-map skill

`/product-map [<dir>]` runs `pending`, writes the descriptions waiting, gives them to `describe` and runs `build`. Only you start it. It can read the app's code but not change it, and it doesn't publish.

Install it as a plugin, from this folder or from GitHub:

```
/plugin marketplace add ianflanagan1/product-map
/plugin install product-map@product-map
```

## Getting the map to colleagues

The map lives in the app's repository, where it's reviewed with the code. The report-problem plugin is public and has no maps: each machine keeps the maps it may see in `~/.claude/product-maps/`, which the skill reads each time it runs. So a map reaches colleagues apart from the plugin, and only those you give it to.

The folder is `product-maps` in Claude Code's own folder, on each system:

| System | Folder |
|---|---|
| macOS | `~/.claude/product-maps/`, that is `/Users/<you>/.claude/product-maps/` |
| Linux | `~/.claude/product-maps/`, that is `/home/<you>/.claude/product-maps/` |
| Windows | `%USERPROFILE%\.claude\product-maps\`, that is `C:\Users\<you>\.claude\product-maps\` |

With `CLAUDE_CONFIG_DIR` set, it's `product-maps` in that folder instead. Getting a map there:

1. On every push to main, the app's CI runs `build` (Dog Cafe's is `.github/workflows/product-map.yml`). When the map would change, Claude describes what's new and the workflow opens a pull request with the new map, so a person reads it before colleagues do.
2. Once that's merged, `product-map publish ~/.claude/product-maps` in the app's repository installs it on your machine. For a colleague, give them the folder `docs/product-map/map/` to save as `<name>` in their `product-maps` folder, where `<name>` is the app's name in lower case with hyphens, as `publish` names it.
3. Their next report uses it. Nothing to restart or update.

## Adapters

An adapter reads one kind of app into `facts.App`; everything after works for any. `dog-cafe` reads apps laid out like Dog Cafe: controllers listed in `config/routerRegisterFromAttributes.php` and routed by `#[Get]`-style attributes, pages in `resources/views/pages/<page>/`, form checks in `FormRequests`, messages in `ErrorCode.php` and choices in `src/Enums`. To read another kind, such as a Laravel app from `php artisan route:list --json` and its Blade templates and lang files, add a module to `adapters/` with a `scan(source, static)` function, list it in `adapters/__init__.py`, and test it against a miniature app in `tests/conftest.py`.

## Setup

```sh
cd ~/projects/cli/product-map
devbox run setup   # uv sync, building .venv
```

That also links `product-map` into `~/.local/bin`, and says so if that folder isn't on your PATH.

## Development

```sh
devbox run test    # pytest
devbox run lint    # ruff check and format
```
