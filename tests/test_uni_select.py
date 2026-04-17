import unittest

from bs4 import BeautifulSoup

from declarative_scraper.uni_selector import _parse_selector, select


class TestSelect(unittest.TestCase):

    def test_parse_selector_plain(self) -> None:
        base, mode = _parse_selector("div.class")
        self.assertEqual(base, "div.class")
        self.assertIsNone(mode)

    def test_parse_selector_text(self) -> None:
        base, mode = _parse_selector("div.class::text")
        self.assertEqual(base, "div.class")
        self.assertEqual(mode, "text")

    def test_parse_selector_attr(self) -> None:
        base, mode = _parse_selector("a::attr(href)")
        self.assertEqual(base, "a")
        self.assertEqual(mode, "attr:href")

    def test_select_text(self) -> None:
        html = "<div><p>hello</p><p>world</p></div>"
        node = BeautifulSoup(html, "html.parser")
        result = select(node, "p::text")
        self.assertEqual(result, ["hello", "world"])

    def test_select_attr(self) -> None:
        html = '<div><a href="/one">A</a><a href="/two">B</a></div>'
        node = BeautifulSoup(html, "html.parser")
        result = select(node, "a::attr(href)")
        self.assertEqual(result, ["/one", "/two"])

    def test_select_plain(self) -> None:
        html = "<ul><li>a</li><li>b</li></ul>"
        node = BeautifulSoup(html, "html.parser")
        result = select(node, "li", as_strings=True)
        self.assertEqual(result, ["<li>a</li>", "<li>b</li>"])

    def test_select_no_match(self) -> None:
        html = "<div>hello</div>"
        node = BeautifulSoup(html, "html.parser")
        result = select(node, "span::text")
        self.assertEqual(result, [])

    def test_select_attr_missing(self) -> None:
        html = "<a>no href</a>"
        node = BeautifulSoup(html, "html.parser")
        result = select(node, "a::attr(href)")
        self.assertEqual(result, [])

    def test_select_text_ignores_nested_tags(self) -> None:
        html = "<p>hello <span>world</span></p>"
        node = BeautifulSoup(html, "html.parser")
        result = select(node, "p::text")
        self.assertEqual(result, ["hello "])

    def test_select_xpath_text(self) -> None:
        html = "<div><p>hello</p><p>world</p></div>"
        node = BeautifulSoup(html, "html.parser")
        result = select(node, "//p/text()")
        self.assertEqual(result, ["hello", "world"])

    def test_select_xpath_on_full_html_document(self) -> None:
        """XPath selector must work on a full HTML document (DOCTYPE + html/head/body).
        lxml.etree.fromstring raises XMLSyntaxError on such input; lxml.html.fromstring handles it."""
        html = (
            "<!DOCTYPE html>\n"
            "<html><head><title>Test</title></head>"
            '<body><p class="target">found</p></body></html>'
        )
        node = BeautifulSoup(html, "html.parser")
        result = select(node, "//p[@class='target']/text()")
        self.assertEqual(result, ["found"])

    def test_select_xpath_function_normalize_space(self) -> None:
        """XPath expressions starting with a function (not / or ./) must be detected as XPath."""
        html = "<div>  hello world  </div>"
        node = BeautifulSoup(html, "html.parser")
        result = select(node, "normalize-space(//div)")
        self.assertEqual(result, ["hello world"])
