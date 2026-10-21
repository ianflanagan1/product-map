"""What a product map says about an app, as read from its code: its pages, the things people do
in it, what's on every page, its messages and its words. An adapter reads these for one kind of
app; everything after works the same for any."""

import hashlib
import json
from dataclasses import asdict, dataclass, field


@dataclass
class Entry:
    """A page, or something people do, such as deleting their account. Each gets a description
    in plain words, written once by Claude and kept while its facts stay the same."""

    kind: str
    """page or action."""
    id: str
    name: str
    """A page's title, or an action's method and address."""
    paths: list[str] = field(default_factory=list)
    login: bool = False
    """Whether only people logged in can use it."""
    texts: list[str] = field(default_factory=list)
    controls: list[str] = field(default_factory=list)
    links: list[list[str]] = field(default_factory=list)
    """Each link's words and where it goes."""
    messages: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    """What the developers wrote about it in the code. Shown to Claude to describe it, and left
    out of the map."""

    @property
    def key(self) -> str:
        return f"{self.kind}:{self.id}"

    def facts(self) -> dict:
        return asdict(self)

    def fingerprint(self) -> str:
        """Changes whenever anything known about the entry does, so its description is written
        again."""
        encoded = json.dumps(self.facts(), sort_keys=True, ensure_ascii=False).encode()
        return hashlib.sha256(encoded).hexdigest()[:16]


@dataclass
class App:
    navigation: list[list[str]] = field(default_factory=list)
    """The links on every page: their words and where they go."""
    everywhere: list[str] = field(default_factory=list)
    """The buttons and fields on every page."""
    pages: list[Entry] = field(default_factory=list)
    actions: list[Entry] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    """Messages any page can show."""
    words: dict[str, list[str]] = field(default_factory=dict)
    """Each set of named choices the app offers, such as venue types, and its choices."""

    def entries(self) -> list[Entry]:
        return [*self.pages, *self.actions]
