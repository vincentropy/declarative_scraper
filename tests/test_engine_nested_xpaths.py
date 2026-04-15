from declarative_scraper.engine import ParseEngine
from declarative_scraper.models import ParseSpec, FieldSpec

HTML = """
<html>
  <body>
    <div class="item">
      <span class="title">Item 1</span>
      <span class="price">$10</span>
    </div>
    <div class="item">
      <span class="title">Item 2</span>
      <span class="price">$20</span>
    </div>
  </body>
</html>
"""


def test_engine_nested_fields_with_xpaths():
    spec = ParseSpec(
        name="test",
        fields={
            "items": FieldSpec(
                selector="//div[@class='item']",
                multiple=True,
                fields={
                    "title": FieldSpec(selector="//span[@class='title']/text()"),
                    "price": FieldSpec(selector="//span[@class='price']/text()"),
                },
            )
        },
    )
    engine = ParseEngine(spec)
    output = engine.parse(HTML)
    assert "items" in output.data
    items = output.data["items"]
    assert isinstance(items, list)
    assert len(items) == 2
    assert items[0]["title"] == "Item 1"
    assert items[0]["price"] == "$10"
    assert items[1]["title"] == "Item 2"
    assert items[1]["price"] == "$20"
