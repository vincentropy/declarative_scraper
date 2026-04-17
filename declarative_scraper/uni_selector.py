import re
from typing import Literal, cast, overload

import lxml.etree
import lxml.html
from bs4 import BeautifulSoup, NavigableString, Tag
from soupsieve import SelectorSyntaxError

_PSEUDO_RE = re.compile(r"::(text|attr\(([^)]+)\))\s*$")


def _xpath_results_to_tags(results: list[object] | str) -> list[Tag] | list[str]:
    """Convert lxml XPath results to BeautifulSoup Tags."""
    if isinstance(results, str):
        return [results]
    tags: list[Tag] | list[str] = []
    all_elements = all(isinstance(r, lxml.etree._Element) for r in results)  # pylint: disable=protected-access
    all_strings = all(isinstance(r, str) for r in results)
    if all_strings:
        return cast(list[str], results)
    if all_elements:
        for r in results:
            html = lxml.html.tostring(r, encoding="unicode")  # type: ignore
            soup = BeautifulSoup(html, "html.parser")
            if soup.contents:
                tags.append(soup.contents[0])  # type: ignore
        return tags

    raise ValueError(f"Expected all XPath results to be either strings or elements, but got: {results}")


def _parse_selector(css: str) -> tuple[str, str | None]:
    """Split selector into (base, mode) stripping ::text / ::attr(...)."""
    m = _PSEUDO_RE.search(css)
    if not m:
        return css, None
    base = css[: m.start()]
    if m.group(1) == "text":
        return base, "text"
    return base, f"attr:{m.group(2)}"


def _select_css(node: Tag | BeautifulSoup, css: str) -> list[str] | list[Tag]:
    """Run a CSS selector and return matched strings."""

    base, mode = _parse_selector(css)
    tags = node.select(base) if base.strip() else []

    if mode == "text":
        results: list[str] = []
        for tag in tags:
            for child in tag.children:
                if isinstance(child, NavigableString) and not isinstance(child, Tag):
                    results.append(str(child))
        return results

    if mode is not None and mode.startswith("attr:"):
        attr_name = mode[5:]
        results = []
        for tag in tags:
            val = tag.get(attr_name)
            if val is not None:
                results.append(" ".join(val) if isinstance(val, list) else str(val))
        return results

    return tags


@overload
def select(
    node: Tag | BeautifulSoup,
    selector: str,
) -> list[Tag] | list[str]: ...
@overload
def select(
    node: Tag | BeautifulSoup,
    selector: str,
    assert_tags: Literal[True],
    assert_strings: Literal[False] = False,
) -> list[Tag]: ...
@overload
def select(
    node: Tag | BeautifulSoup,
    selector: str,
    assert_tags: Literal[False] = False,
    assert_strings: Literal[True] = True,
) -> list[str]: ...
@overload
def select(
    node: Tag | BeautifulSoup,
    selector: str,
    *,
    as_strings: Literal[True] = True,
) -> list[str]: ...


def select(
    node: Tag | BeautifulSoup,
    selector: str,
    assert_tags: bool = False,
    assert_strings: bool = False,
    as_strings: bool = False,
) -> list[Tag] | list[str]:
    """Select elements using CSS or XPath selector."""
    results: list[Tag] | list[str] = []
    try:
        # CSS selector
        tags = _select_css(node, selector)
        results = tags
    except SelectorSyntaxError:
        # XPath selector
        root = lxml.html.fromstring(str(node))
        xpath_results = cast(list[object] | str, root.xpath(selector))
        str_or_tag = _xpath_results_to_tags(xpath_results)
        results = str_or_tag

    all_tags = all(isinstance(r, Tag) for r in results)
    all_strings = all(isinstance(r, str) for r in results)
    if assert_tags and not all_tags:
        raise ValueError(f"Expected all results to be Tags, but got: {results}")
    if assert_strings and not all_strings:
        raise ValueError(f"Expected all results to be strings, but got: {results}")
    if as_strings:
        return [str(r) for r in results]
    return results
