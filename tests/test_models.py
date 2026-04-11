import unittest
from declarative_scraper import models


class TestModels(unittest.TestCase):
    def test_parser_spec_model_reads_example_spec(self):
        spec = models.ParseSpec.model_validate_yaml(
            "tests/example_data/example_spec.yaml"
        )
        self.assertEqual(spec.name, "example_spec_name")
        self.assertIn("title", spec.fields)
        self.assertIn("links", spec.fields)
        self.assertEqual(spec.fields["title"].type, models.FieldType.TEXT)
        self.assertEqual(spec.fields["links"].type, models.FieldType.LINK)
