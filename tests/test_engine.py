# pylint: disable=protected-access
import unittest

from bs4 import BeautifulSoup

from py_decs import FieldSpec, ParseEngine, ParseSpec, ProcessorSpec
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


class TestParseFieldPath(unittest.TestCase):

    def setUp(self) -> None:
        self.spec = ParseSpec(
            name="test",
            fields={
                "title": FieldSpec(selector="//h1/text()"),
                "link": FieldSpec(selector="//a/@href"),
                "person": FieldSpec(
                    selector="//div[@class='person']",
                    fields={
                        "name": FieldSpec(selector="//span[1]/text()"),
                        "age": FieldSpec(selector="//span[2]/text()"),
                    },
                ),
            },
        )
        self.html = (
            "<h1>Hello</h1>"
            '<a href="/page">Link</a>'
            '<div class="person"><span class="name">Alice</span><span class="age">30</span></div>'
        )
        self.engine = ParseEngine(self.spec)

    def test_top_level_field(self) -> None:
        result = self.engine.parse(self.html, field_path="title")
        self.assertEqual(result.data, {"title": "Hello"})

    def test_top_level_field_excludes_others(self) -> None:
        result = self.engine.parse(self.html, field_path="link")
        self.assertNotIn("title", result.data)
        self.assertEqual(result.data, {"link": "/page"})

    def test_nested_field(self) -> None:
        result = self.engine.parse(self.html, field_path="person.name")
        self.assertEqual(result.data, {"person": {"name": "Alice"}})

    def test_nested_field_sibling_excluded(self) -> None:
        result = self.engine.parse(self.html, field_path="person.age")
        self.assertNotIn("name", result.data)
        self.assertEqual(result.data, {"person": {"age": "30"}})

    def test_nested_field_children_included(self) -> None:
        result = self.engine.parse(self.html, field_path="person")
        self.assertNotIn("name", result.data)
        self.assertEqual(result.data, {"person": {"age": "30", "name": "Alice"}})

    def test_missing_top_level_field_raises(self) -> None:
        with self.assertRaises(KeyError):
            self.engine.parse(self.html, field_path="nonexistent")

    def test_missing_nested_field_raises(self) -> None:
        with self.assertRaises(KeyError):
            self.engine.parse(self.html, field_path="person.nonexistent")

    def test_navigate_into_flat_field_raises(self) -> None:
        with self.assertRaises(KeyError):
            self.engine.parse(self.html, field_path="title.something")

    def test_no_field_path_returns_all(self) -> None:
        result = self.engine.parse(self.html)
        self.assertIn("title", result.data)
        self.assertIn("link", result.data)
        self.assertIn("person", result.data)


class TestParseFieldPathMultiple(unittest.TestCase):

    def setUp(self) -> None:
        self.spec = ParseSpec(
            name="test",
            fields={
                "connections": FieldSpec(
                    selector="//div[@class='connection']",
                    multiple=True,
                    fields={
                        "name": FieldSpec(selector="//span[1]/text()"),
                        "role": FieldSpec(selector="//span[2]/text()"),
                    },
                ),
                "title": FieldSpec(selector="//h1/text()"),
            },
        )
        self.html = (
            "<h1>Profile</h1>"
            '<div class="connection"><span class="name">Alice</span><span class="role">Engineer</span></div>'
            '<div class="connection"><span class="name">Bob</span><span class="role">Manager</span></div>'
        )
        self.engine = ParseEngine(self.spec)

    def test_multiple_intermediate_collects_list(self) -> None:
        result = self.engine.parse(self.html, field_path="connections.name")
        self.assertEqual(result.data, {"connections": [{"name": "Alice"}, {"name": "Bob"}]})

    def test_multiple_intermediate_other_field(self) -> None:
        result = self.engine.parse(self.html, field_path="connections.role")
        self.assertEqual(result.data, {"connections": [{"role": "Engineer"}, {"role": "Manager"}]})

    def test_multiple_intermediate_excludes_sibling_top_fields(self) -> None:
        result = self.engine.parse(self.html, field_path="connections.name")
        self.assertNotIn("title", result.data)
        self.assertNotIn("role", result.data)


class TestParseAndValidate(unittest.TestCase):

    def test_parse_and_validate_passes(self) -> None:
        spec = ParseSpec(
            name="test",
            fields={
                "title": FieldSpec(selector="h1::text", required=True),
            },
        )
        engine = ParseEngine(spec)
        output = engine.parse_and_validate("<h1>Hello</h1>")
        self.assertEqual(output.data, {"title": "Hello"})

    def test_parse_and_validate_raises_on_invalid(self) -> None:
        spec = ParseSpec(
            name="test",
            fields={
                "title": FieldSpec(selector="h1::text", required=True),
            },
        )
        engine = ParseEngine(spec)
        with self.assertRaises(ValueError):
            engine.parse_and_validate("<div>No title</div>")
