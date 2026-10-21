"""Reading PHP source without running PHP."""

from product_map import php


def test_string_literals_are_read_with_their_escapes():
    assert php.strings("""$a = 'it\\'s' . "tab\\there" . 'a\\\\b';""") == [
        "it's",
        "tab\there",
        "a\\b",
    ]


def test_a_route_built_from_constants_and_literals_is_evaluated():
    consts = php.constants("protected const string ROOT = '/list'; const API = '/api';")
    assert consts == {"ROOT": "/list", "API": "/api"}
    assert php.evaluate("self::ROOT . '/:town'", consts) == "/list/:town"
    assert php.evaluate("static::API", consts) == "/api"


def test_an_expression_it_cannot_work_out_is_none():
    assert php.evaluate("self::MISSING", {}) is None
    assert php.evaluate("route('x')", {}) is None


def test_methods_carry_their_attributes_docblock_and_body():
    code = """class C {
        #[Get('/a')]
        #[Get('/b')]
        /**
         * Show the page.
         * @return Response
         */
        public function show(Request $r): Response { if ($x === '}') { return 1; } // }
            return 2; }

        abstract protected function later(): void;

        public function other() { return "{"; }
    }"""
    show, later, other = php.methods(code)
    assert show.name == "show"
    assert show.attributes == [("Get", "'/a'"), ("Get", "'/b'")]
    assert show.doc == "Show the page."
    assert show.params == "Request $r"
    assert "return 2;" in show.body
    assert later.name == "later" and later.body == ""
    assert other.attributes == [] and other.doc == ""
