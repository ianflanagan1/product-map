"""What a person sees on a page: the text, buttons, fields and links in its HTML, read from a PHP
template or from strings in JavaScript, without rendering either."""

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

from product_map import php

_PHP_BLOCK = re.compile(r"<\?(?:php|=)(.*?)(?:\?>|\Z)", re.S)
_HIDDEN = {"script", "style", "template", "noscript"}
_INDEX = re.compile(r"\[\s*(?:" + php.STRING + r")\s*\]")
"""An array index, such as ['name'], whose string is a key, not something shown."""
_JS_STRING = re.compile(r"'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"")
_JS_SHOWN = re.compile(r"\b(?:confirm|alert)\s*\(\s*(" + _JS_STRING.pattern + r")")
_JS_ASSIGNED = re.compile(r"\.(?:innerHTML|textContent|innerText)\s*=\s*\(?\s*(.*)")


@dataclass
class Visible:
    texts: list[str] = field(default_factory=list)
    controls: list[str] = field(default_factory=list)
    """Buttons, fields and menus, each as what kind it is and what it says: `button: Submit`."""
    links: list[tuple[str, str]] = field(default_factory=list)
    """Each link's words and where it goes."""


def from_template(source: str) -> Visible:
    """What a PHP template shows: its HTML, and the HTML in the strings its PHP echoes."""
    return from_html(template_html(source))


def template_html(source: str) -> str:
    """The template's HTML, each PHP block replaced by the HTML in its string literals. The
    literals in one statement are joined, so `'<a href="' . $url . '">Website</a>'` reads as a
    link saying Website."""

    def html_in(block: re.Match[str]) -> str:
        code = _INDEX.sub("", block[1])
        statements = ("".join(php.strings(s)) for s in code.split(";"))
        return " ".join(s for s in statements if "<" in s and ">" in s)

    return _PHP_BLOCK.sub(html_in, source)


def title(head_source: str) -> str | None:
    """The page's title, or None when it has none, or part of it is filled in as it's shown."""
    match = re.search(r"<title>(.*?)</title>", head_source, re.S | re.I)
    if not match or "<?" in match[1]:
        return None
    return _clean(match[1]) or None


def from_html(html: str) -> Visible:
    parser = _Reader()
    parser.feed(html)
    parser.close()
    return parser.visible


def from_script(source: str) -> list[str]:
    """The fixed messages a script shows: in confirm() and alert(), and in the plain strings it
    puts into the page."""
    messages: list[str] = []
    for match in _JS_SHOWN.finditer(source):
        messages.append(_clean(php.unquote(match[1])))
    for match in _JS_ASSIGNED.finditer(source):
        for literal in _JS_STRING.findall(match[1]):
            text = php.unquote(literal)
            if "<" in text:
                messages += from_html(text).texts
            else:
                messages.append(_clean(text))
    return _unique(m for m in messages if _wordy(m))


class _Reader(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.visible = Visible()
        self._hidden = 0
        self._link: tuple[str, list[str]] | None = None
        self._button: list[str] | None = None
        self._label: list[str] | None = None
        self._labels: dict[str, str] = {}
        """Each label's words, by the id of the field it's for."""
        self._ticks: list[tuple[int, str, str]] = []
        """Each tick box or choice: where it is in controls, its kind and its id or name."""
        self._unlabelled: list[int] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {name: value or "" for name, value in attrs}
        if tag in _HIDDEN:
            self._hidden += 1
        elif tag == "a" and "href" in a:
            self._link = (a["href"], [])
        elif tag == "button":
            self._button = []
        elif tag == "label":
            self._label = []
            if a.get("for"):
                self._labels.setdefault(a["for"], "")
                self._label_for = a["for"]
            else:
                self._label_for = None
        elif tag == "img" and a.get("alt") and self._link:
            self._link[1].append(a["alt"])
        elif tag == "input":
            kind = a.get("type", "text")
            if kind in ("submit", "button") and a.get("value"):
                self._control("button", a["value"])
            elif kind in ("checkbox", "radio"):
                name = "tick box" if kind == "checkbox" else "choice"
                self._ticks.append((len(self.visible.controls), name, a.get("id", "")))
                self._control(name, a.get("id") or a.get("name") or kind)
                if self._label is not None and not self._label_for:
                    self._unlabelled.append(len(self.visible.controls) - 1)
            elif kind not in ("hidden", "submit", "button"):
                self._control("field", a.get("placeholder") or a.get("name") or kind)
        elif tag == "textarea":
            self._control("text box", a.get("placeholder") or a.get("name") or "")
        elif tag == "select":
            self._control("menu", a.get("name") or "")

    def handle_endtag(self, tag: str) -> None:
        if tag in _HIDDEN:
            self._hidden = max(0, self._hidden - 1)
        elif tag == "a" and self._link:
            href, words = self._link
            label = _clean(" ".join(words))
            if label:
                self.visible.links.append((label, href))
            self._link = None
        elif tag == "button" and self._button is not None:
            self._control("button", " ".join(self._button))
            self._button = None
        elif tag == "label" and self._label is not None:
            words = _clean(" ".join(self._label))
            if self._label_for:
                self._labels[self._label_for] = words
            for index in self._unlabelled:
                kind = self.visible.controls[index].split(":", 1)[0]
                self.visible.controls[index] = f"{kind}: {words}"
            self._label = None
            self._unlabelled = []

    def close(self) -> None:
        super().close()
        for index, kind, ident in self._ticks:
            if self._labels.get(ident):
                self.visible.controls[index] = f"{kind}: {self._labels[ident]}"

    def handle_data(self, data: str) -> None:
        if self._hidden:
            return
        if self._label is not None:
            self._label.append(data)
        if self._link:
            self._link[1].append(data)
        elif self._button is not None:
            self._button.append(data)
        elif _wordy(text := _clean(data)):
            self.visible.texts.append(text)

    def _control(self, kind: str, label: str) -> None:
        label = _clean(label)
        if label:
            self.visible.controls.append(f"{kind}: {label}")


def _clean(text: str) -> str:
    return " ".join(text.split())


def _wordy(text: str) -> bool:
    return any(char.isalnum() for char in text)


def _unique(items) -> list[str]:
    return list(dict.fromkeys(items))
