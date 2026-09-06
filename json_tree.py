#!/usr/bin/env python3
"""Display JSON structure or JSON Schema as a tree, using only the standard library."""

import argparse
import json
import os
import sys
from dataclasses import dataclass, field

# Managed by json-tree installer.


def path_matches(text):
    expanded = os.path.expanduser(text)
    directory, partial = os.path.split(expanded)
    display_directory = os.path.split(text)[0]
    try:
        with os.scandir(directory or ".") as entries:
            return sorted(os.path.join(display_directory, entry.name) +
                          (os.sep if entry.is_dir() else "")
                          for entry in entries if entry.name.startswith(partial))
    except OSError:
        return []


def prompt_file():
    try:
        import readline
    except ImportError:
        readline = None
        print("Tab completion unavailable: Python readline is not installed.", file=sys.stderr)
    if readline is not None:
        previous = readline.get_completer()
        delimiters = readline.get_completer_delims()
        matches = []

        def complete(text, state):
            if state == 0:
                matches[:] = path_matches(text)
            return matches[state] if state < len(matches) else None

        readline.set_completer_delims("")
        readline.set_completer(complete)
        readline.parse_and_bind("tab: complete")
    try:
        while True:
            print("JSON file (Tab to complete, Ctrl-D to cancel): ", end="", file=sys.stderr, flush=True)
            path = input()
            if path:
                return os.path.expanduser(path)
            print("Enter a file path.", file=sys.stderr)
    finally:
        if readline is not None:
            readline.set_completer(previous)
            readline.set_completer_delims(delimiters)


@dataclass
class Shape:
    types: set = field(default_factory=set)
    properties: dict = field(default_factory=dict)
    counts: dict = field(default_factory=dict)
    objects: int = 0
    items: object = None

    def add(self, value):
        kind = ("null" if value is None else "boolean" if isinstance(value, bool)
                else "object" if isinstance(value, dict) else "array" if isinstance(value, list)
                else "string" if isinstance(value, str) else "integer" if isinstance(value, int)
                else "number")
        self.types.add(kind)
        if kind == "object":
            self.objects += 1
            for key, child in value.items():
                self.properties.setdefault(key, Shape()).add(child)
                self.counts[key] = self.counts.get(key, 0) + 1
        elif kind == "array":
            if self.items is None:
                self.items = Shape()
            for child in value:
                self.items.add(child)


@dataclass
class Node:
    label: str
    children: list = field(default_factory=list)


def name(value):
    # JSON quoting keeps unusual keys (including terminal control characters) safe.
    return json.dumps(value, ensure_ascii=True)


def inferred_node(shape, label, sort=False):
    types = shape.types - {"integer"} if "number" in shape.types else shape.types
    node = Node(f"{label}: {' | '.join(sorted(types)) or 'unknown'}")
    keys = sorted(shape.properties) if sort else shape.properties
    for key in keys:
        optional = "?" if shape.counts[key] < shape.objects else ""
        node.children.append(inferred_node(shape.properties[key], name(key) + optional, sort))
    if shape.items is not None:
        node.children.append(inferred_node(shape.items, "[]", sort))
    return node


def schema_node(schema, label, sort=False):
    if isinstance(schema, bool):
        return Node(f"{label}: {'any' if schema else 'never'}")
    if not isinstance(schema, dict):
        raise ValueError("each schema must be an object or boolean")
    kind = schema.get("type")
    if kind is None:
        kind = "object" if "properties" in schema else "array" if "items" in schema or "prefixItems" in schema else "any"
    if isinstance(kind, list):
        kind = " | ".join(kind)
    details = []
    for key in ("$ref", "format", "const", "enum"):
        if key in schema:
            details.append(f"{key}={json.dumps(schema[key], ensure_ascii=True)}")
    node = Node(f"{label}: {kind}" + (" (" + ", ".join(details) + ")" if details else ""))
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    for key in sorted(properties) if sort else properties:
        node.children.append(schema_node(properties[key], name(key) + ("" if key in required else "?"), sort))
    for index, child in enumerate(schema.get("prefixItems", [])):
        node.children.append(schema_node(child, f"[{index}]", sort))
    if "items" in schema:
        items = schema["items"]
        if isinstance(items, list):
            for index, child in enumerate(items):
                node.children.append(schema_node(child, f"[{index}]", sort))
        else:
            node.children.append(schema_node(items, "[]", sort))
    for keyword in ("oneOf", "anyOf", "allOf"):
        if keyword in schema:
            node.children.append(Node(keyword, [schema_node(child, f"[{i}]", sort) for i, child in enumerate(schema[keyword])]))
    for keyword in ("$defs", "definitions", "patternProperties"):
        if keyword in schema:
            entries = schema[keyword]
            node.children.append(Node(keyword, [schema_node(entries[key], name(key), sort) for key in (sorted(entries) if sort else entries)]))
    for keyword in ("additionalProperties", "contains", "not", "if", "then", "else"):
        if keyword in schema:
            node.children.append(schema_node(schema[keyword], keyword, sort))
    return node


def render(node, ascii_only=False, max_depth=None):
    branch, last, vertical = ("|-- ", "`-- ", "|   ") if ascii_only else ("├── ", "└── ", "│   ")
    yield node.label

    def walk(parent, prefix, depth):
        children = parent.children
        if max_depth is not None and depth > max_depth:
            if children:
                yield prefix + last + ("..." if ascii_only else "…")
            return
        for index, child in enumerate(children):
            final = index == len(children) - 1
            yield prefix + (last if final else branch) + child.label
            yield from walk(child, prefix + ("    " if final else vertical), depth + 1)

    yield from walk(node, "", 1)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  json-tree data.json --sort
  json-tree schema.json --schema
  cat data.json | json-tree
  json-tree --ascii -L 2

Without FILE, read piped stdin or prompt for a path in a terminal.
The prompt completes paths with Tab; enter paths with spaces without quotes.
? means optional; [] describes array elements. Inference describes the sample only.""")
    parser.add_argument("file", nargs="?", help="JSON file, or - to explicitly read stdin")
    parser.add_argument("--schema", action="store_true", help="interpret input as JSON Schema instead of sample JSON")
    parser.add_argument("--ascii", action="store_true", help="use ASCII tree connectors")
    parser.add_argument("--sort", action="store_true", help="sort object keys")
    parser.add_argument("-L", "--max-depth", type=int, help="limit displayed depth (root is 0)")
    args = parser.parse_args(argv)
    if args.max_depth is not None and args.max_depth < 0:
        parser.error("max depth must be nonnegative")
    try:
        if args.file is None:
            args.file = prompt_file() if sys.stdin.isatty() else "-"
        def reject_constant(value):
            raise ValueError(f"invalid JSON constant: {value}")

        if args.file == "-":
            value = json.load(sys.stdin, parse_constant=reject_constant)
        else:
            with open(os.path.expanduser(args.file), encoding="utf-8-sig") as stream:
                value = json.load(stream, parse_constant=reject_constant)
        if args.schema:
            node = schema_node(value, "$", args.sort)
        else:
            shape = Shape()
            shape.add(value)
            node = inferred_node(shape, "$", args.sort)
        print("\n".join(render(node, args.ascii, args.max_depth)))
        return 0
    except (EOFError, KeyboardInterrupt):
        print("\njson-tree: cancelled", file=sys.stderr)
        return 130
    except (OSError, ValueError, TypeError, AttributeError, RecursionError) as error:
        print(f"json-tree: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
