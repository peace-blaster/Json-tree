import subprocess
import sys
import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path

from json_tree import Shape, inferred_node, render, schema_node, path_matches, main


class TreeTests(unittest.TestCase):
    def test_path_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "some file.json").touch()
            (root / "some folder").mkdir()
            self.assertEqual(path_matches(str(root / "some")),
                             [str(root / "some file.json"), str(root / "some folder") + "/"])
            self.assertEqual(path_matches(str(root / "missing" / "x")), [])

    def test_terminal_fallback_and_cancel(self):
        with patch("sys.stdin.isatty", return_value=True), patch("json_tree.prompt_file", side_effect=EOFError), patch("sys.stderr"):
            self.assertEqual(main([]), 130)
        with patch("sys.stdin.isatty", return_value=True), patch("json_tree.prompt_file", return_value=str(Path(__file__).with_name("example.json"))) as prompt, patch("sys.stdout"):
            self.assertEqual(main([]), 0)
            prompt.assert_called_once()

    def test_install_uninstall(self):
        root = Path(__file__).parent
        with tempfile.TemporaryDirectory(prefix="json tree test ") as directory:
            def run(script):
                return subprocess.run(["sh", str(root / script), "--prefix", directory], text=True, capture_output=True)
            target = Path(directory) / "bin" / "json-tree"
            self.assertEqual(run("install.sh").returncode, 0)
            result = subprocess.run([str(target), "--help"], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn("Examples:", result.stdout)
            self.assertEqual(run("install.sh").returncode, 0)
            self.assertEqual(run("uninstall.sh").returncode, 0)
            self.assertFalse(target.exists())
            self.assertEqual(run("uninstall.sh").returncode, 0)
            target.write_text("unrelated program")
            self.assertEqual(run("install.sh").returncode, 1)
            self.assertEqual(run("uninstall.sh").returncode, 1)
            self.assertEqual(target.read_text(), "unrelated program")

    def infer(self, value):
        shape = Shape()
        shape.add(value)
        return "\n".join(render(inferred_node(shape, "$")))

    def test_array_merges_fields_and_marks_missing(self):
        self.assertEqual(self.infer([{"id": 1}, {"id": 2.5, "active": True}]),
                         '$: array\n└── []: object\n    ├── "id": number\n    └── "active"?: boolean')

    def test_mixed_and_empty_arrays(self):
        self.assertIn("boolean | integer | null | string", self.infer([True, 1, None, "a"]))
        self.assertEqual(self.infer([]), "$: array\n└── []: unknown")

    def test_keys_are_escaped(self):
        self.assertIn('"a\\n\\u001b"', self.infer({"a\n\x1b": 1}))

    def test_schema(self):
        node = schema_node({"type": "object", "required": ["id"], "properties": {
            "id": {"type": "integer"}, "next": {"$ref": "#"}}}, "$")
        output = "\n".join(render(node))
        self.assertIn('"id": integer', output)
        self.assertIn('"next"?: any ($ref="#")', output)
        self.assertEqual(schema_node(False, "$").label, "$: never")

    def test_depth_and_ascii(self):
        shape = Shape()
        shape.add({"a": {"b": 1}})
        self.assertEqual("\n".join(render(inferred_node(shape, "$"), True, 1)),
                         '$: object\n`-- "a": object\n    `-- ...')

    def test_cli_invalid_input_and_stdin(self):
        script = str(Path(__file__).with_name("json_tree.py"))
        for source in ("{", "NaN"):
            result = subprocess.run([sys.executable, script], input=source, text=True, capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("json-tree:", result.stderr)
        result = subprocess.run([sys.executable, script], input="null", text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "$: null\n")


if __name__ == "__main__":
    unittest.main()
