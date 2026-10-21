"""Reading the parts of PHP source a product map needs, without running PHP: string literals,
class constants, and methods with their attributes, docblock and body."""

import re
from dataclasses import dataclass

STRING = r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\""
_STRING = re.compile(STRING, re.S)
_CONSTANT = re.compile(r"\bconst\s+(?:\??[\w\\]+\s+)?(\w+)\s*=\s*(" + STRING + r")\s*;", re.S)
_FUNCTION = re.compile(r"\bfunction\s+(\w+)\s*\(")
_ATTRIBUTE = re.compile(r"#\[\s*([\w\\]+)\s*\((.*?)\)\s*\]", re.S)
_DOCBLOCK = re.compile(r"/\*\*(.*?)\*/", re.S)
_ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "$": "$", "'": "'"}


@dataclass(frozen=True)
class Method:
    name: str
    attributes: list[tuple[str, str]]
    """Each attribute's short name and the source of its arguments."""
    doc: str
    """The docblock's text, without its tags."""
    params: str
    body: str


def unquote(literal: str) -> str:
    """The value of a PHP string literal."""
    quote, inner = literal[0], literal[1:-1]
    if quote == "'":
        return re.sub(r"\\([\\'])", r"\1", inner)
    return re.sub(r"\\(.)", lambda m: _ESCAPES.get(m[1], "\\" + m[1]), inner)


def strings(code: str) -> list[str]:
    """The values of the string literals in code, in order."""
    return [unquote(match[0]) for match in _STRING.finditer(code)]


def constants(code: str) -> dict[str, str]:
    """The class's string constants by name."""
    return {match[1]: unquote(match[2]) for match in _CONSTANT.finditer(code)}


def evaluate(expression: str, consts: dict[str, str]) -> str | None:
    """The value of a string expression made of literals and self:: or static:: constants joined
    by `.`, or None for anything else."""
    parts: list[str] = []
    rest = expression.strip()
    while rest:
        if literal := _STRING.match(rest):
            parts.append(unquote(literal[0]))
            rest = rest[literal.end() :]
        elif constant := re.match(r"(?:self|static)::(\w+)", rest):
            if constant[1] not in consts:
                return None
            parts.append(consts[constant[1]])
            rest = rest[constant.end() :]
        else:
            return None
        rest = rest.strip()
        if rest.startswith("."):
            rest = rest[1:].strip()
        elif rest:
            return None
    return "".join(parts)


def methods(code: str) -> list[Method]:
    """The class's methods, with the attributes and docblock written before each, between it and
    the method or class before it."""
    found: list[Method] = []
    previous_end = code.find("{") + 1
    for match in _FUNCTION.finditer(code):
        if match.start() < previous_end:
            continue
        open_paren = match.end() - 1
        close_paren = _matching(code, open_paren, "(", ")")
        open_brace = code.find("{", close_paren)
        semicolon = code.find(";", close_paren)
        if open_brace == -1 or (semicolon != -1 and semicolon < open_brace):
            body, end = "", semicolon + 1
        else:
            end = _matching(code, open_brace, "{", "}") + 1
            body = code[open_brace + 1 : end - 1]
        before = code[previous_end : match.start()]
        attributes = [(m[1].rsplit("\\", 1)[-1], m[2]) for m in _ATTRIBUTE.finditer(before)]
        docs = _DOCBLOCK.findall(before)
        found.append(
            Method(
                match[1],
                attributes,
                doc_text(docs[-1]) if docs else "",
                code[open_paren + 1 : close_paren],
                body,
            )
        )
        previous_end = end
    return found


def doc_text(doc: str) -> str:
    """A docblock's prose: its lines without leading stars, up to its first tag."""
    lines: list[str] = []
    for line in doc.splitlines():
        line = line.strip().lstrip("*").strip()
        if line.startswith("@"):
            break
        lines.append(line)
    return " ".join(" ".join(lines).split())


def _matching(code: str, start: int, opening: str, closing: str) -> int:
    """The index of the bracket closing the one at start, skipping strings and comments."""
    depth = 0
    i = start
    while i < len(code):
        char = code[i]
        if char in "'\"":
            literal = _STRING.match(code, i)
            i = literal.end() if literal else i + 1
            continue
        if code.startswith("//", i) or char == "#" and not code.startswith("#[", i):
            newline = code.find("\n", i)
            i = len(code) if newline == -1 else newline + 1
            continue
        if code.startswith("/*", i):
            end = code.find("*/", i + 2)
            i = len(code) if end == -1 else end + 2
            continue
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return len(code)
