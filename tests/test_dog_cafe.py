"""Reading an app laid out like Dog Cafe."""

from product_map.adapters import dog_cafe


def scan(repo):
    return dog_cafe.scan(repo / "app", repo / "static")


def test_each_page_has_its_title_addresses_and_what_is_on_it(repo):
    pages = {page.id: page for page in scan(repo).pages}
    home = pages["home"]
    assert (home.name, home.paths, home.login) == ("Tiny Cafe", ["/"], False)
    assert home.texts == ["Welcome & hello", "Today's specials"]
    assert home.links == [["See the menu", "/menu/"]]
    assert home.notes == ["Render the home page."]


def test_a_page_rendered_by_a_helper_is_found_with_its_login_check(repo):
    note = {page.id: page for page in scan(repo).pages}["note"]
    assert note.paths == ["/note"]
    assert note.login is True
    assert note.name == "Note"
    assert note.controls == [
        "tick box: Sugar",
        "choice: Oat milk",
        "text box: note",
        "menu: cup",
        "button: Save ✓",
        "button: Send",
    ]


def test_a_page_with_no_route_is_still_listed_without_an_address(repo):
    thanks = {page.id: page for page in scan(repo).pages}["thanks"]
    assert (thanks.name, thanks.paths, thanks.texts) == ("Thanks", [], ["Thanks!"])


def test_a_script_on_every_page_goes_to_every_page_and_others_to_their_page(repo):
    app = scan(repo)
    pages = {page.id: page for page in app.pages}
    assert pages["home"].messages == ["Searching...", "No results"]
    assert pages["note"].messages == []
    assert "Leave this page?" in app.messages


def test_a_form_s_checks_become_the_messages_people_see(repo):
    [action] = scan(repo).actions
    assert (action.id, action.paths) == ("POST /note", ["/note"])
    assert action.messages == [
        "`note` is required",
        "`note` can't be longer than 200",
        "`stars` can't be larger than 5",
    ]
    assert action.notes == ["Save a note. On failure, show the form again."]


def test_reading_data_behind_the_scenes_is_left_out(repo):
    assert all("/api/" not in path for e in scan(repo).entries() for path in e.paths)


def test_the_layout_gives_every_page_s_links_fields_and_the_error_page(repo):
    app = scan(repo)
    assert app.navigation == [["Account", "/account"], ["Login", "/login"], ["Home", "/"]]
    assert app.everywhere == ["field: Search drinks"]
    assert "An error page showing only a number: 403" in app.messages


def test_named_choices_are_read_in_words(repo):
    assert scan(repo).words == {"Drink size": ["Small", "Extra Large"]}
