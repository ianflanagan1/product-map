"""The kinds of app product-map can read, by the name .workspace.toml's [product-map] gives them."""

from collections.abc import Callable
from pathlib import Path

from product_map.adapters import dog_cafe
from product_map.facts import App

ADAPTERS: dict[str, Callable[[Path, Path | None], App]] = {"dog-cafe": dog_cafe.scan}
