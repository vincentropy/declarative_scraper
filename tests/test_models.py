import unittest

from spextract import models


class TestModels(unittest.TestCase):
    def test_parser_spec_model_reads_example_spec(self):
        spec = models.ParseSpec.from_yaml_file("tests/example_data/example_spec.yaml")
        self.assertEqual(spec.name, "example_spec")
        self.assertIn("page_title", spec.fields)
        self.assertIn("cities", spec.fields)
        self.assertEqual(spec.fields["page_title"].type, models.FieldType.TEXT)
        self.assertEqual(spec.fields["cities"].multiple, True)
        self.assertEqual(spec.fields["cities"].fields["name"].type, models.FieldType.TEXT)
        self.assertEqual(spec.fields["cities"].fields["url"].type, models.FieldType.LINK)
