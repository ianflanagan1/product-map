"""What a person sees, read from templates and scripts."""

from product_map import visible


def test_text_buttons_fields_and_links_are_read_and_hidden_parts_are_not():
    shown = visible.from_html(
        "<h1>Hi &amp; bye</h1><script>x = 'no'</script><p> Two   words </p>"
        '<a href="/x"><img alt="Home"/></a><button>Go</button>'
        '<input type="hidden" value="secret"/><input placeholder="Town"/>'
        '<input type="submit" value="Send"/><textarea name="note"></textarea>'
    )
    assert shown.texts == ["Hi & bye", "Two words"]
    assert shown.links == [("Home", "/x")]
    assert shown.controls == ["button: Go", "field: Town", "button: Send", "text box: note"]


def test_a_tick_box_or_choice_is_named_by_its_label():
    shown = visible.from_html(
        '<label for="a">Cafes</label><input type="checkbox" id="a" name="typesCafes"/>'
        '<label><input type="radio" name="m"/> Oat milk</label>'
    )
    assert shown.controls == ["tick box: Cafes", "choice: Oat milk"]


def test_html_a_template_echoes_from_php_is_read_and_its_array_keys_are_not():
    shown = visible.from_template(
        "<?php $e = 1; ?><p>Plain</p><?= '<a href=\"/v/' . $e($p['slug']) . '\">Website</a>' ?>"
    )
    assert shown.texts == ["Plain"]
    assert shown.links == [("Website", "/v/")]


def test_a_title_filled_in_as_it_is_shown_is_no_title():
    assert visible.title("<title>Map</title>") == "Map"
    assert visible.title("<title><?= $name ?> - Cafe</title>") is None
    assert visible.title("<link/>") is None


def test_a_script_s_fixed_messages_are_read_and_built_ones_are_not():
    script = """
        if (!confirm('Delete it? This is irreversible.')) return;
        box.innerHTML = '<div>Searching...</div>';
        box.textContent = "No results";
        box.innerHTML = `<b>${n}</b>`;
        box.textContent = count;
    """
    assert visible.from_script(script) == [
        "Delete it? This is irreversible.",
        "Searching...",
        "No results",
    ]
