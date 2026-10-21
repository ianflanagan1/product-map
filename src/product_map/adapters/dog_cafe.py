"""Apps built like Dog Cafe: controllers listed in config/routerRegisterFromAttributes.php, routed
by #[Get]-style attributes; pages in resources/views/pages/<page>/head.php and body.php inside
resources/views/layouts/main.php; form inputs checked by the rules in each FormRequest; messages
in src/Framework/Errors/ErrorCode.php; and named choices in src/Enums."""

import re
from pathlib import Path

from product_map import php, visible
from product_map.facts import App, Entry

ROUTES = {"Get", "Post", "Put", "Patch", "Delete"}
_FILTER_TYPES = {"FILTER_VALIDATE_INT": "int", "FILTER_VALIDATE_FLOAT": "float"}


def scan(source: Path, static: Path | None) -> App:
    """The app whose PHP is in source and whose public scripts are in static."""
    app = App()
    pages_dir = source / "resources" / "views" / "pages"
    pages = {d.name: _page(d, static) for d in sorted(pages_dir.iterdir()) if d.is_dir()}
    scripts = {d.name: _scripts(d / "head.php") for d in pages_dir.iterdir() if d.is_dir()}
    headed = [
        set(s) for page_id, s in scripts.items() if (pages_dir / page_id / "head.php").exists()
    ]
    shared = set.intersection(*headed) if headed else set()
    """The scripts on every page with a head of its own: their messages can show anywhere."""
    for page_id, page in pages.items():
        page.messages = _unique(
            m for name in scripts[page_id] if name not in shared for m in _script(static, name)
        )

    messages = _error_messages(source)
    for controller in _controllers(source):
        code = controller.read_text()
        consts = php.constants(code)
        methods = {m.name: m for m in php.methods(code)}
        uses = _uses(code, source)
        for method in methods.values():
            for name, args in method.attributes:
                path = php.evaluate(args, consts) if name in ROUTES else None
                if path is None:
                    continue
                reached = _reached(method, methods)
                rendered = _unique(
                    p for m in reached for p in re.findall(r"page:\s*'(\w+)'", m.body)
                )
                login = any("->guard(" in m.body for m in reached)
                checks = _input_messages(method, uses, source, messages)
                if name == "Get" and rendered:
                    for page_id in rendered:
                        if page_id in pages:
                            page = pages[page_id]
                            page.paths = _unique([*page.paths, path])
                            page.login = page.login or login
                            page.notes = _unique(
                                [*page.notes, method.doc] if method.doc else page.notes
                            )
                elif not (name == "Get" and path.startswith("/api/")):
                    app.actions.append(
                        Entry(
                            "action",
                            f"{name.upper()} {path}",
                            f"{name.upper()} {path}",
                            [path],
                            login,
                            messages=checks,
                            notes=[method.doc] if method.doc else [],
                        )
                    )

    layout = visible.from_template((source / "resources/views/layouts/main.php").read_text())
    app.navigation = [list(link) for link in _unique(tuple(link) for link in layout.links)]
    app.everywhere = _unique(layout.controls)
    app.pages = list(pages.values())
    app.messages = _unique(
        [m for name in sorted(shared) for m in _script(static, name)] + _error_pages(source)
    )
    app.words = _enums(source)
    return app


def _page(directory: Path, static: Path | None) -> Entry:
    head = directory / "head.php"
    body = directory / "body.php"
    shown = visible.from_template(body.read_text()) if body.exists() else visible.Visible()
    name = (visible.title(head.read_text()) if head.exists() else None) or _words(directory.name)
    return Entry(
        "page",
        directory.name,
        name,
        texts=_unique(shown.texts),
        controls=_unique(shown.controls),
        links=[list(link) for link in _unique(tuple(link) for link in shown.links)],
    )


def _scripts(head: Path) -> list[str]:
    if not head.exists():
        return []
    return _unique(re.findall(r"src=\"/js/([\w-]+)\.js\"", head.read_text()))


def _script(static: Path | None, name: str) -> list[str]:
    path = static / "js" / f"{name}.js" if static else None
    return visible.from_script(path.read_text()) if path and path.exists() else []


def _controllers(source: Path) -> list[Path]:
    listing = (source / "config" / "routerRegisterFromAttributes.php").read_text()
    uses = _uses(listing, source)
    return [uses[name] for name in re.findall(r"(\w+)::class", listing) if name in uses]


def _uses(code: str, source: Path) -> dict[str, Path]:
    """Each class the file imports from App\\, by its short name, and the file it's in."""
    found: dict[str, Path] = {}
    for full in re.findall(r"^use\s+App\\([\w\\]+);", code, re.M):
        found[full.rsplit("\\", 1)[-1]] = source / "src" / (full.replace("\\", "/") + ".php")
    return found


def _reached(method: php.Method, methods: dict[str, php.Method]) -> list[php.Method]:
    """The method and every method of its class it calls, directly or not."""
    seen = {method.name: method}
    queue = [method]
    while queue:
        for called in re.findall(r"\$this->(\w+)\(", queue.pop().body):
            if called in methods and called not in seen:
                seen[called] = methods[called]
                queue.append(methods[called])
    return list(seen.values())


def _error_messages(source: Path) -> dict[str, str]:
    code = (source / "src" / "Framework" / "Errors" / "ErrorCode.php").read_text()
    return {
        name: php.unquote(literal)
        for name, literal in re.findall(r"self::(\w+)\s*=>\s*(" + php.STRING + ")", code)
    }


def _rule_errors(source: Path) -> dict[tuple[str, str], str]:
    """The ErrorCode each rule gives, by the rule's name and the type it checks."""
    factory = (source / "src" / "Framework" / "Validation" / "RuleFactory.php").read_text()
    uses = _uses(factory, source)
    found: dict[tuple[str, str], str] = {}
    for case in re.split(r"\bcase\s+", factory)[1:]:
        name = re.match(r"'(\w+)'", case)
        if not name:
            continue
        for kind, cls in re.findall(r"'(string|int|float)'\s*=>\s*new\s+(\w+)", case) or [
            (kind, cls) for cls in re.findall(r"return\s+new\s+(\w+)", case)[:1] for kind in ("*",)
        ]:
            path = uses.get(cls)
            code = path.read_text() if path and path.exists() else ""
            if error := re.search(r"ErrorCode::(\w+)", code):
                found[(name[1], kind)] = error[1]
    return found


def _input_messages(
    method: php.Method, uses: dict[str, Path], source: Path, messages: dict[str, str]
) -> list[str]:
    """The messages the inputs a route takes can fail with, as people see them."""
    found: list[str] = []
    rules = None
    for request in re.findall(r"(\w+Request)\s+\$", method.params):
        path = uses.get(request)
        if not path or not path.exists():
            continue
        rules = rules if rules is not None else _rule_errors(source)
        code = path.read_text()
        for field, spec in re.findall(
            r"'(\w+)'\s*=>\s*\[\s*'filter'(.*?)(?='\w+'\s*=>\s*\[\s*'filter'|\Z)", code, re.S
        ):
            kind = _FILTER_TYPES.get(
                next(iter(re.findall(r"'type'\s*=>\s*(\w+)", spec)), ""), "string"
            )
            listed = re.search(r"'rules'\s*=>\s*\[(.*?)\]", spec, re.S)
            for rule in php.strings(listed[1]) if listed else []:
                name, _, parameter = rule.partition(":")
                error = rules.get((name, kind)) or rules.get((name, "*"))
                if error and error in messages:
                    text = messages[error].replace(":field", field).replace(":parameter", parameter)
                    found.append(text)
    return _unique(found)


def _error_pages(source: Path) -> list[str]:
    codes = set()
    for path in (source / "src").rglob("*.php"):
        code = path.read_text()
        codes.update(re.findall(r"->error\(\s*(\d{3})", code))
        codes.update(re.findall(r"jsonError\(\s*(\d{3})", code))
    if not codes:
        return []
    return [f"An error page showing only a number: {', '.join(sorted(codes))}"]


def _enums(source: Path) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in sorted((source / "src" / "Enums").glob("*.php")):
        code = path.read_text()
        enum = re.search(r"\benum\s+(\w+)", code)
        if enum:
            cases = re.findall(r"\bcase\s+(\w+)\s*[=;]", code)
            found[_words(enum[1])] = [_words(case, sentence=False) for case in cases]
    return found


def _words(name: str, sentence: bool = True) -> str:
    """CamelCase or camelCase as words: VenueOrderBy as Venue order by, or, not as a sentence,
    UnitedKingdom as United Kingdom."""
    words = re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+", name)
    if not words:
        return name
    if sentence:
        return " ".join([words[0].capitalize(), *(w.lower() for w in words[1:])])
    return " ".join(words)


def _unique(items) -> list:
    return list(dict.fromkeys(items))
