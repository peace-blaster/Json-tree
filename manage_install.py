#!/usr/bin/env python3
"""Install or uninstall json-tree on Linux."""

import argparse
import os
from pathlib import Path
import sys
import tempfile


MARKER = b"# Managed by json-tree installer."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "uninstall"))
    parser.add_argument("--prefix", type=Path, default=Path.home() / ".local",
                        help="installation prefix (default: ~/.local); executable goes in PREFIX/bin")
    args = parser.parse_args()
    target = args.prefix.expanduser().absolute() / "bin" / "json-tree"
    try:
        if sys.platform != "linux":
            parser.error("this installer supports Linux")
        if sys.version_info < (3, 7):
            parser.error("Python 3.7 or newer is required")
        if target.is_symlink() or (target.exists() and
                (not target.is_file() or MARKER not in target.read_bytes())):
            raise ValueError(f"refusing to replace or remove an unmanaged file: {target}")
        if args.action == "uninstall":
            if target.exists():
                target.unlink()
                print(f"Removed {target}")
            else:
                print(f"Already uninstalled: {target}")
            return 0
        source = Path(__file__).with_name("json_tree.py").read_bytes()
        if MARKER not in source:
            raise ValueError("source is missing the installer marker")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".json-tree-", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(source)
            temporary.chmod(0o755)
            temporary.replace(target)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        print(f"Installed {target}")
        if str(target.parent) not in os.environ.get("PATH", "").split(os.pathsep):
            print(f"Add {target.parent} to PATH to run json-tree by name.")
        return 0
    except (OSError, ValueError) as error:
        print(f"json-tree installer: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
