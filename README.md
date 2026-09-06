# json-tree

A dependency-free Python 3 command-line visualizer for JSON structure, with Linux `tree` style output.

Install on Linux with Python 3.7 or newer:

```bash
./install.sh
export PATH="$HOME/.local/bin:$PATH"
json-tree --help
```

The installer copies the executable to `~/.local/bin/json-tree`. Add the PATH line to your shell configuration if that directory is not already on PATH. Re-running the installer updates the installed copy. No dependencies are downloaded and no shell configuration is edited.

Uninstall with `./uninstall.sh`. Both scripts accept `--prefix /path/to/prefix` and `--help`; use the same prefix when uninstalling. For a system-wide installation, use `sudo ./install.sh --prefix /usr/local` and `sudo ./uninstall.sh --prefix /usr/local`. Uninstallation removes only the managed executable, leaving the source directory intact. Both scripts refuse to overwrite or remove an unrelated executable or symlink.

Run `json-tree` without a file in a terminal to get an interactive file-path prompt. Press Tab to complete file or directory names, and Tab twice to list ambiguous matches. Paths containing spaces should be entered without quotes; `~/` paths are supported. Ctrl-D or Ctrl-C cancels with exit status 130. Completion uses Python's standard `readline` module; if unavailable, the prompt still works without completion. This completion is inside the prompt, not a shell completion extension.

Piped or redirected input is read automatically; explicit `-` always reads stdin. Options also work with the prompt, for example `json-tree --schema --sort`. `json-tree --help` displays argparse usage, options, and examples.

```bash
python3 json_tree.py example.json
python3 json_tree.py /path/to/data.json --sort
cat example.json | python3 json_tree.py
python3 json_tree.py /path/to/schema.json --schema
python3 json_tree.py example.json --ascii -L 2
```

Example output:

```text
$: object
├── "name": string
├── "enabled": boolean
├── "users": array
│   └── []: object
│       ├── "id": integer
│       ├── "name": string
│       └── "email"?: string
└── "settings": object
    ├── "theme": string
    └── "retries": integer
```

By default, the tool infers structure from a JSON sample. Array elements are combined, mixed types are shown with `|`, and fields missing from some objects have `?`. Empty arrays have `unknown` element types. Inference describes only the supplied sample, not a guarantee about future data. Values are not printed in sample mode.

Use `--schema` to display an existing JSON Schema: required fields, properties, items, tuple items, unions, definitions, references, and selected annotations. References are displayed without expansion or fetching. This is a structural viewer, not a schema validator; not every validation keyword is displayed.

`--sort` sorts property names. `--ascii` uses ASCII connectors. `-L N` limits the displayed depth, with the root at zero. Input is read completely into memory; the depth option limits output, not parsing. Invalid JSON or unreadable files produce an error and exit status 1.

Run tests with `python3 -m unittest -v` from this directory.
