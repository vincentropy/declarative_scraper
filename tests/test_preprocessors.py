import unittest

from py_decs.processors import ProcessorName, apply_processor


class TestProcessors(unittest.TestCase):

    def test_strip(self) -> None:
        self.assertEqual(apply_processor(ProcessorName.STRIP, "  hello  "), "hello")

    def test_to_int(self) -> None:
        self.assertEqual(apply_processor(ProcessorName.TO_INT, "42"), 42)

    def test_to_float(self) -> None:
        result = apply_processor(ProcessorName.TO_FLOAT, "3.14")
        assert isinstance(result, float)
        self.assertAlmostEqual(result, 3.14)

    def test_lowercase(self) -> None:
        result = apply_processor(ProcessorName.LOWERCASE, "Hello")
        self.assertEqual(result, "hello")

    def test_uppercase(self) -> None:
        result = apply_processor(ProcessorName.UPPERCASE, "hello")
        self.assertEqual(result, "HELLO")

    def test_join(self) -> None:
        self.assertEqual(apply_processor(ProcessorName.JOIN, ["a", "b", "c"]), "a b c")

    def test_join_with_separator(self) -> None:
        self.assertEqual(apply_processor(ProcessorName.JOIN, ["a", "b"], [","]), "a,b")

    def test_regex(self) -> None:
        self.assertEqual(apply_processor(ProcessorName.REGEX, "price: 42$", [r"\d+"]), "42")

    def test_split(self) -> None:
        self.assertEqual(apply_processor(ProcessorName.SPLIT, "a,b,c", [","]), ["a", "b", "c"])

    def test_index(self) -> None:
        self.assertEqual(apply_processor(ProcessorName.INDEX, [10, 20, 30], ["1"]), 20)

    def test_unknown_processor(self) -> None:
        with self.assertRaises(ValueError):
            apply_processor("nonexistent", "value")  # type: ignore


if __name__ == "__main__":
    unittest.main()
