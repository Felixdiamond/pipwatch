# Pipwatch

[![PyPI version](https://badge.fury.io/py/pipwatch.svg)](https://badge.fury.io/py/pipwatch)
[![CI](https://github.com/Felixdiamond/pipwatch/workflows/CI/badge.svg)](https://github.com/Felixdiamond/pipwatch/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Detect import statements in Python files and install the corresponding PyPI packages.

Pipwatch parses your Python files for imports, filters out standard library modules, maps import names to PyPI package names where they differ (e.g. `PIL` to `pillow`, `cv2` to `opencv-python`), and installs whatever is missing.

## Features

### Import Detection
- Parses import statements using the AST module and filters out standard library modules
- Also detects `# pip install` comments and version specifiers in your code
- Maps import names to correct PyPI package names (e.g. `sklearn` -> `scikit-learn`)
- Skips packages that are already installed

### Mapping Registry
- Package mappings hosted on GitHub and fetched at runtime
- Local cache with 24-hour TTL so it doesn't hit the network on every run
- Falls back to bundled `mappings.json` when offline
- New mappings can be added via pull request

### CLI Flags
- `--dry-run` - Preview what would be installed without installing anything
- `--generate` - Generate a `requirements.txt` file from detected dependencies
- `--verbose` - Enable detailed debug logging
- `--yes` - Auto-confirm installations (useful for CI)
- `--output` - Specify custom output path for generated requirements files
- `--update-mappings` - Fetch latest mappings from GitHub
- `--clear-cache` - Clear cached mappings
- `--show-mappings` - Show mapping statistics

### Directory Scanning
- Point pipwatch at a directory instead of a single file to scan everything
- Automatically skips `.venv`, `node_modules`, `__pycache__`, `build`, `dist`, and other junk directories

### Installer Support
- Works with both pip and [uv](https://github.com/astral-sh/uv) — if uv is on your PATH, pipwatch will use it automatically

## Installation

```bash
pip install pipwatch
```

or with uv:
```bash
uv add pipwatch
```

For development:
```bash
pip install pipwatch[dev]
```

## Usage

### Basic Usage

Analyze a single file:
```bash
pipwatch script.py
```

Analyze all Python files in the current directory & subdirectories:
```bash
pipwatch .
```

Analyze all Python files in a specific folder:
```bash
pipwatch myfolder/
```

### Dry Run (Preview Only)

See what would be installed without installing:
```bash
pipwatch script.py --dry-run
```

Or for an entire directory:
```bash
pipwatch . --dry-run
```

Example output:
```
INFO: Analyzing script.py...
INFO: Found the following dependencies from import statements:
INFO:   • bs4 → beautifulsoup4
INFO:   • numpy
INFO:   • pandas

[DRY RUN] Would install the following packages:
  • beautifulsoup4
  • numpy
  • pandas
```

### Generate Requirements File

Create a `requirements.txt` from your code:
```bash
pipwatch script.py --generate
```

Or with a custom output path:
```bash
pipwatch script.py --generate --output my-requirements.txt
```

### Auto-Install (No Prompts)

For automation and CI:
```bash
pipwatch script.py --yes
```

### Verbose Mode

Get detailed debug information:
```bash
pipwatch script.py --verbose
```

### Manage Mappings

Update mappings from GitHub:
```bash
pipwatch --update-mappings
```

Show mapping statistics:
```bash
pipwatch --show-mappings
```

Clear cached mappings:
```bash
pipwatch --clear-cache
```

## Package Name Mappings

Pipwatch includes 50+ mappings for cases where the import name differs from the PyPI package name:

| Import Name | Package Name |
|------------|--------------|
| `PIL` | `pillow` |
| `cv2` | `opencv-python` |
| `sklearn` | `scikit-learn` |
| `bs4` | `beautifulsoup4` |
| `yaml` | `pyyaml` |
| `Crypto` | `pycryptodome` |
| `jwt` | `PyJWT` |
| And more... | |

## How It Works

1. **Parse** - Parses your Python file using the AST module
2. **Filter** - Removes standard library imports
3. **Analyze** - Scans for `# pip install` comments and version specifiers
4. **Map** - Maps import names to PyPI package names
5. **Check** - Checks which packages are already installed
6. **Install/Generate** - Installs missing packages or generates `requirements.txt`

### Mapping Resolution

The mapping system loads from three sources, trying each in order:

```
┌─────────────────┐
│  mappings.json  │ (GitHub)
│   (Remote)      │
└────────┬────────┘
         │ Fetch (once per day)
         ▼
┌─────────────────┐
│  Local Cache    │ (~/.pipwatch/)
│  (24hr TTL)     │
└────────┬────────┘
         │ Fallback
         ▼
┌─────────────────┐
│  Bundled File   │ (Offline support)
│  (Built-in)     │
└─────────────────┘
```

### Contributing Mappings

Found a missing mapping? See [docs/CONTRIBUTING_MAPPINGS.md](docs/CONTRIBUTING_MAPPINGS.md) for how to add one.

## Development

### Setup

```bash
git clone https://github.com/Felixdiamond/pipwatch.git
cd pipwatch
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest tests/
```

With coverage:
```bash
pytest tests/ --cov=src/pipwatch --cov-report=term-missing
```

### Code Formatting

```bash
black src/ tests/
isort src/ tests/
ruff check src/ tests/ --fix
```

### Update Mappings

Use the helper script to add or discover import-to-package mappings in
`src/pipwatch/mappings.json`.

Add a single mapping (validated against PyPI):

```bash
python scripts/populate_mappings.py add PIL pillow --category image-processing
```

Preview without writing:

```bash
python scripts/populate_mappings.py add PIL pillow --category image-processing --dry-run
```

Discover mappings from your installed packages and preview:

```bash
python scripts/populate_mappings.py discover
```

Apply discovered mappings:

```bash
python scripts/populate_mappings.py discover --apply
```

Preview discovered mappings without writing:

```bash
python scripts/populate_mappings.py discover --apply --dry-run
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT License](LICENSE)

---

Created by [Felix Dawodu](https://github.com/Felixdiamond)
