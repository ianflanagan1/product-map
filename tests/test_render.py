"""The product map as Markdown."""

import tomllib

from product_map import render
from product_map.facts import App, Entry

TRACKER = {
    "kind": "jira",
    "site": "shop.atlassian.net",
    "space": "SHOP",
    "labels": ["report"],
    "stages": {"needs-codebase": "Triage"},
}


def shop() -> tuple[App, dict]:
    favs = Entry(
        "page",
        "favs",
        "Favourites",
        ["/favs"],
        True,
        ["Saved"],
        ["button: Remove"],
        [["Home", "/"]],
        ["No results"],
        ["Render favs."],
    )
    thanks = Entry("page", "thanks", "Thanks")
    save = Entry("action", "POST /api/v1/favs", "POST /api/v1/favs", ["/api/v1/favs"], True)
    delete = Entry("action", "DELETE /account", "DELETE /account", ["/account"], True)
    app = App(
        [["List", "/list"]],
        ["field: Search town"],
        [favs, thanks],
        [save, delete],
        ["Leave?"],
        {"Venue type": ["Cafe", "Bar"]},
    )
    described = {
        "page:favs": {"description": "Your saved places."},
        "action:POST /api/v1/favs": {"title": "Saving a favourite", "description": "Saved."},
        "action:DELETE /account": {"title": "Deleting your account", "description": "Gone."},
    }
    return app, described


def test_the_map_is_an_index_a_file_for_each_area_and_one_for_the_choices():
    app, described = shop()
    files = render.files(app, described, "Shop", "v1", TRACKER)
    assert sorted(files) == ["areas/favs.md", "areas/other.md", "choices.md", "index.md"]


def test_the_index_has_the_front_matter_what_is_on_every_page_and_each_area_s_contents():
    app, described = shop()
    index = render.files(app, described, "Shop", "v1", TRACKER)["index.md"]
    assert index.startswith(render.header("Shop", "v1", TRACKER))
    assert index.endswith(
        "\n".join(
            [
                "## On every page",
                "",
                "- Links: “List” (`/list`)",
                "- Field: “Search town”",
                "- Can show: “Leave?”",
                "",
                "## Areas",
                "",
                "Each area's pages, and the things people do there, are in its file in `areas/`,"
                " next to this one, with what's on each page and the messages it can show."
                " The choices the app offers are in `choices.md`.",
                "",
                "- Favourites, `areas/favs.md`: Favourites (`/favs`). Saving a favourite.",
                "- Other pages and things people do, `areas/other.md`: Thanks."
                " Deleting your account.",
                "",
            ]
        )
    )


def test_an_area_file_has_its_pages_then_the_things_people_do_there_in_full():
    app, described = shop()
    area = render.files(app, described, "Shop", "v1", TRACKER)["areas/favs.md"]
    assert area == "\n".join(
        [
            "# Favourites, in Shop",
            "",
            "## Pages",
            "",
            "### Favourites",
            "",
            "`/favs` · only people logged in",
            "",
            "Your saved places.",
            "",
            "- Shows: “Saved”",
            "- Button: “Remove”",
            "- Links: “Home” (`/`)",
            "- Can show: “No results”",
            "",
            "## Things people do",
            "",
            "### Saving a favourite",
            "",
            "`/api/v1/favs` · only people logged in",
            "",
            "Saved.",
            "",
        ]
    )


def test_the_choices_file_lists_each_set_of_choices():
    app, described = shop()
    choices = render.files(app, described, "Shop", "v1", TRACKER)["choices.md"]
    assert choices == "# Choices Shop offers\n\n- Venue type: Cafe, Bar\n"


def test_a_page_s_area_is_the_first_fixed_part_of_its_address():
    pages = [
        Entry("page", "list", "List", ["/:townStr", "/list/:townStr"]),
        Entry("page", "billing", "Invoices", ["/billing/invoices"]),
        Entry("page", "plans", "Plans", ["/billing/plans"]),
        Entry("page", "home", "Home", ["/"]),
    ]
    areas = render.areas(App(pages=pages))
    assert [(area.slug, area.title, [p.id for p in area.pages]) for area in areas] == [
        ("list", "List", ["list"]),
        ("billing", "Invoices", ["billing", "plans"]),
        ("home", "Home", ["home"]),
    ]


def test_an_action_joins_the_area_of_its_address_skipping_api_and_its_version():
    page = Entry("page", "favs", "Favourites", ["/favs"])
    action = Entry("action", "POST /api/v2/favs/:id", "POST", ["/api/v2/favs/:id"])
    [area] = render.areas(App(pages=[page], actions=[action]))
    assert [a.id for a in area.actions] == ["POST /api/v2/favs/:id"]


def test_pages_without_an_address_and_actions_with_no_page_of_their_own_are_in_other():
    page = Entry("page", "error", "Error")
    action = Entry("action", "POST /logout", "POST /logout", ["/logout"])
    [area] = render.areas(App(pages=[page], actions=[action]))
    assert (area.slug, [p.id for p in area.pages], [a.id for a in area.actions]) == (
        "other",
        ["error"],
        ["POST /logout"],
    )


def test_what_developers_wrote_in_the_code_is_left_out():
    page = Entry("page", "favs", "Favourites", notes=["Render a page via FavouriteController."])
    files = render.files(App(pages=[page]), {}, "Shop", "v1", TRACKER)
    assert not any("Controller" in text for text in files.values())


def test_addresses_name_what_goes_in_them_in_words():
    assert render.address("/:townStr") == "/<town>"
    assert render.address("/venue/:venueReference") == "/venue/<venue reference>"
    assert render.address("/favs/:extId") == "/favs/<ext id>"


def test_the_header_opens_with_toml_front_matter_naming_the_app_its_version_and_tracker():
    text = render.header("Shop", "v1.2.0, 2026-10-01", TRACKER)
    assert text.startswith("+++\n")
    assert tomllib.loads(text.split("+++\n")[1]) == {
        "app": "Shop",
        "built_from": "v1.2.0, 2026-10-01",
        "tracker": TRACKER,
    }


def test_the_front_matter_keeps_strings_that_need_escaping():
    text = render.header('Shop "Pro" \\ 2', "v1", {"site": "s", "space": "S"})
    assert tomllib.loads(text.split("+++\n")[1])["app"] == 'Shop "Pro" \\ 2'


def test_the_header_is_set_apart_from_what_follows():
    text = render.header("Shop", "v1.2.0, 2026-10-01", TRACKER)
    assert text.endswith(
        "+++\n\n# Shop\n\nWhat people can see and do in Shop, in the words its"
        " screens use, for anyone describing a problem with it. Built by product-map: build it"
        " again rather than editing it.\n\n"
    )


def test_a_map_differing_only_in_the_version_it_was_built_from_says_the_same():
    app, described = shop()
    old = render.files(app, described, "Shop", "v1.1.0", TRACKER)
    assert render.same(old, render.files(app, described, "Shop", "v1.2.0", TRACKER))
    moved = TRACKER | {"space": "STORE"}
    assert not render.same(old, render.files(app, described, "Shop", "v1.2.0", moved))
    app.pages[0].texts.append("New")
    assert not render.same(old, render.files(app, described, "Shop", "v1.2.0", TRACKER))
