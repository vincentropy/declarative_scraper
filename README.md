# A Declarative HTML Scraper for Python

This package provides a simple way to declare what data should be extracted from an HTML document in a configuration file.

This enables sharing of scraping logic across projects and teams without the risk of executing untrusted code. It also allows for easier maintenance and updates to scraping logic without needing to modify the underlying codebase.

## CLI

The package includes a Click-based CLI with two commands:

```bash
spextract parse spec.yaml <path to html file or directory>
spextract validate spec.yaml expected-results.yaml
```

`parse` emits YAML in the same expected-results format used by `validate`, so you can capture known-good output and re-run validation later.

## How to use

### Build a configuration file

You can write a configuration file with the provided ParserSpec class.

```python
import spextract

spec = spextract.ParserSpec(
    name="example_parser",
    description="An example parser for demonstration purposes.",
    fields=[
        spextract.FieldSpec(
            name="title",
            selector="h1.title::text",
            type=spextract.FieldType.TEXT,
        ),
        spextract.FieldSpec(
            name="links",
            selector="a.link::attr(href)",
            type=spextract.FieldType.LINK,
            multiple=True,
        ),
        spextract.FieldSpec(
            name="author",
            selector="div.author",
            type=spextract.FieldType.OBJECT,
            fields=[
                spextract.FieldSpec(
                    name="name",
                    selector="span.name::text",
                    type=spextract.FieldType.TEXT,
                ),
                spextract.FieldSpec(
                    name="profile_url",
                    selector="a.profile::attr(href)",
                    type=spextract.FieldType.LINK,
                ),
            ]
        ),
    ]
)
```
