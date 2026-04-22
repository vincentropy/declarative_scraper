# pylint: disable=protected-access
import unittest

from bs4 import BeautifulSoup

from py_decs.engine import ParseEngine
from py_decs.models import FieldSpec, ParseSpec, ProcessorSpec
from py_decs.processors import ProcessorName


class TestApplyProcessors(unittest.TestCase):

    def test_single_processor(self) -> None:
        processors = [ProcessorSpec(name=ProcessorName.STRIP)]
        result = ParseEngine.apply_processors("  hello  ", processors)
        self.assertEqual(result, "hello")

    def test_chained_processors(self) -> None:
        processors = [
            ProcessorSpec(name=ProcessorName.STRIP),
            ProcessorSpec(name=ProcessorName.UPPERCASE),
        ]
        result = ParseEngine.apply_processors("  hello  ", processors)
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
        self.assertEqual(result.data, {"title": "Hello"})

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
        self.assertEqual(result.data, {"title": "Hello", "link": "/page"})


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
        print(field.resolved_processors())
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
