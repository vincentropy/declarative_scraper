# pylint: disable=protected-access
import unittest

from bs4 import BeautifulSoup

from declarative_scraper.engine import ParseEngine
from declarative_scraper.models import FieldSpec, ParseSpec, ProcessorSpec
from declarative_scraper.processors import ProcessorName


class TestParseEngine(unittest.TestCase):

    def test_parse_selector_plain(self) -> None:
        base, mode = ParseEngine._parse_selector("div.class")
        self.assertEqual(base, "div.class")
        self.assertIsNone(mode)

    def test_parse_selector_text(self) -> None:
        base, mode = ParseEngine._parse_selector("div.class::text")
        self.assertEqual(base, "div.class")
        self.assertEqual(mode, "text")

    def test_parse_selector_attr(self) -> None:
        base, mode = ParseEngine._parse_selector("a::attr(href)")
        self.assertEqual(base, "a")
        self.assertEqual(mode, "attr:href")

    def test_select_text(self) -> None:
        html = "<div><p>hello</p><p>world</p></div>"
        node = BeautifulSoup(html, "html.parser")
        result = ParseEngine._select(node, "p::text")
        self.assertEqual(result, ["hello", "world"])

    def test_select_attr(self) -> None:
        html = '<div><a href="/one">A</a><a href="/two">B</a></div>'
        node = BeautifulSoup(html, "html.parser")
        result = ParseEngine._select(node, "a::attr(href)")
        self.assertEqual(result, ["/one", "/two"])

    def test_select_plain(self) -> None:
        html = "<ul><li>a</li><li>b</li></ul>"
        node = BeautifulSoup(html, "html.parser")
        result = ParseEngine._select(node, "li")
        self.assertEqual(result, ["<li>a</li>", "<li>b</li>"])

    def test_select_no_match(self) -> None:
        html = "<div>hello</div>"
        node = BeautifulSoup(html, "html.parser")
        result = ParseEngine._select(node, "span::text")
        self.assertEqual(result, [])

    def test_select_attr_missing(self) -> None:
        html = "<a>no href</a>"
        node = BeautifulSoup(html, "html.parser")
        result = ParseEngine._select(node, "a::attr(href)")
        self.assertEqual(result, [])

    def test_select_text_ignores_nested_tags(self) -> None:
        html = "<p>hello <span>world</span></p>"
        node = BeautifulSoup(html, "html.parser")
        result = ParseEngine._select(node, "p::text")
        self.assertEqual(result, ["hello "])


class TestApplyProcessors(unittest.TestCase):

    def test_single_processor(self) -> None:
        processors = [ProcessorSpec(name=ProcessorName.STRIP)]
        result = ParseEngine._apply_processors("  hello  ", processors)
        self.assertEqual(result, "hello")

    def test_chained_processors(self) -> None:
        processors = [
            ProcessorSpec(name=ProcessorName.STRIP),
            ProcessorSpec(name=ProcessorName.UPPERCASE),
        ]
        result = ParseEngine._apply_processors("  hello  ", processors)
        self.assertEqual(result, "HELLO")


class TestParse(unittest.TestCase):

    def test_parse_single_field(self) -> None:
        spec = ParseSpec(
            name="test",
            fields={
                "title": FieldSpec(selector="h1::text"),
            },
        )
        engine = ParseEngine(spec)
        result = engine.parse("<h1>Hello</h1>")
        self.assertEqual(result, [{"title": "Hello"}])

    def test_parse_multiple_fields(self) -> None:
        spec = ParseSpec(
            name="test",
            fields={
                "title": FieldSpec(selector="h1::text"),
                "link": FieldSpec(selector="a::attr(href)"),
            },
        )
        engine = ParseEngine(spec)
        result = engine.parse('<h1>Hello</h1><a href="/page">Link</a>')
        self.assertEqual(result, [{"title": "Hello", "link": "/page"}])


class TestExtractField(unittest.TestCase):

    def test_single_value(self) -> None:
        node = BeautifulSoup("<p>hello</p>", "html.parser")
        field = FieldSpec(selector="p::text")
        result = ParseEngine._extract_field(node, field)
        self.assertEqual(result, "hello")

    def test_multiple_values(self) -> None:
        node = BeautifulSoup("<p>a</p><p>b</p>", "html.parser")
        field = FieldSpec(selector="p::text", multiple=True)
        result = ParseEngine._extract_field(node, field)
        self.assertEqual(result, ["a", "b"])

    def test_no_match_single(self) -> None:
        node = BeautifulSoup("<div></div>", "html.parser")
        field = FieldSpec(selector="p::text")
        result = ParseEngine._extract_field(node, field)
        self.assertIsNone(result)

    def test_no_match_multiple(self) -> None:
        node = BeautifulSoup("<div></div>", "html.parser")
        field = FieldSpec(selector="p::text", multiple=True)
        result = ParseEngine._extract_field(node, field)
        self.assertEqual(result, [])

    def test_with_processor(self) -> None:
        node = BeautifulSoup("<p>  hello  </p>", "html.parser")
        field = FieldSpec(selector="p::text", processors=[ProcessorName.STRIP])
        result = ParseEngine._extract_field(node, field)
        self.assertEqual(result, "hello")


class TestExtractNested(unittest.TestCase):

    def test_nested_single(self) -> None:
        html = '<div class="item"><h2>Title</h2><span>Detail</span></div>'
        node = BeautifulSoup(html, "html.parser")
        field = FieldSpec(
            selector="div.item",
            fields={
                "title": FieldSpec(selector="h2::text"),
                "detail": FieldSpec(selector="span::text"),
            },
        )
        result = ParseEngine._extract_nested(node, field)
        self.assertEqual(result, {"title": "Title", "detail": "Detail"})

    def test_nested_multiple(self) -> None:
        html = '<div class="item"><p>A</p></div><div class="item"><p>B</p></div>'
        node = BeautifulSoup(html, "html.parser")
        field = FieldSpec(
            selector="div.item",
            multiple=True,
            fields={"name": FieldSpec(selector="p::text")},
        )
        result = ParseEngine._extract_nested(node, field)
        self.assertEqual(result, [{"name": "A"}, {"name": "B"}])

    def test_nested_no_match(self) -> None:
        node = BeautifulSoup("<div></div>", "html.parser")
        field = FieldSpec(
            selector="div.item",
            fields={"name": FieldSpec(selector="p::text")},
        )
        result = ParseEngine._extract_nested(node, field)
        self.assertIsNone(result)
