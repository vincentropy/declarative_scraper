# A Declarative HTML Scraper for Python

This package provides a simple way to declare what data should be extracted from an HTML document in a configuration file.

This enables sharing of scraping logic across projects and teams without the risk of executing untrusted code. It also allows for easier maintenance and updates to scraping logic without needing to modify the underlying codebase.

## How to use

### Build a configuration file

You can write a configuration file with the provided ParserSpec class.

```python
import declarative_scraper as ds

spec = ds.ParserSpec(
    name="example_parser",
    description="An example parser for demonstration purposes.",
    items=[
        ds.FieldSpec(
            name="title",
            selector="h1.title::text",
            type=ds.FieldType.TEXT,
        ),
        ds.FieldSpec(
            name="links",
            selector="a.link::attr(href)",
            type=ds.FieldType.LINK,
            multiple=True,
        )
    ]
)
```
