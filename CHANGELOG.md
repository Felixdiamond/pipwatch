# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.3] - 2026-02-12

### Added
- Directory scanning — run `pipwatch .` or `pipwatch myfolder/` to analyze all Python files recursively
- Smart directory filtering — automatically skips `.venv`, `node_modules`, `__pycache__`, `build`, `dist`, etc.
- uv support — detects if `uv` is available and uses it instead of pip for installs

## [0.0.1] - 2026-02-12

### Added
- Initial release
- Dependency detection from Python import statements
- Automatic package installation
- Dry-run mode
- Requirements generation
- 50+ import-to-package mappings

### Major Rewrite

This is a major overhaul that brings the project to a production-ready state.

### Added

#### Core Features
- **Dry-run mode** (`--dry-run`) - Preview dependencies without installing
- **Requirements generation** (`--generate`) - Create requirements.txt from code
- **Verbose logging** (`--verbose`) - Detailed debug information
- **Auto-confirm mode** (`--yes`) - Skip prompts for automation/CI
- **Custom output paths** (`--output`) - Specify where to save generated files
- **Version support** - Parse and preserve version specifiers from comments (e.g., `>=1.0.0`)

#### Developer Experience
- Progress indicators showing `[1/5] Installing...` during installs
- Improved error messages on failures
- Built-in help text with examples
- 50+ import-to-package mappings (up from 6)

#### Package Mappings
- Added mappings for data science packages (numpy, pandas, sklearn)
- Added mappings for web frameworks (Flask, Django, FastAPI)
- Added mappings for database drivers (psycopg2, mysqlclient, pymongo)
- Added mappings for HTTP libraries (requests, aiohttp, httpx)
- Added mappings for cryptography (pycryptodome, PyJWT, PyNaCl)
- Added mappings for date/time (python-dateutil, arrow, pendulum)
- Added mappings for CLI tools (click, rich, tqdm, colorama)
- And more

#### Testing & Quality
- Test suite with pytest (18+ tests)
- Code coverage tracking with pytest-cov
- GitHub Actions CI/CD testing on Python 3.10-3.13 across Linux, macOS, Windows
- Code formatting with Black, isort, and Ruff
- Type hints throughout
- Pre-commit hooks

#### Documentation
- Expanded README with examples
- Contributing guide
- Changelog

### Changed

#### Breaking Changes
- **Minimum Python version** - Now requires Python 3.10+ (was 3.7+)
- **CLI interface** - Now uses argparse with flags instead of positional args only

#### Improvements
- Replaced `pkg_resources` with `importlib.metadata` (faster, no deprecation warnings)
- Better import detection with `ast.Constant` nodes for Python 3.10+
- Improved normalization of package names
- Structured logging instead of print statements

### Fixed
- AST parsing for modern Python (changed from `ast.Str` to `ast.Constant`)
- Package name normalization (handles underscores vs hyphens)
- Error handling for syntax errors in analyzed files
- UTF-8 encoding issues when reading files

### Technical Debt Resolved
- Removed deprecated `pkg_resources` dependency
- Added proper logging instead of print statements
- Added error handling
- Modernized code with type hints
- Applied consistent code formatting

## [0.1.1] - 2023-XX-XX

### Initial Release
- Basic dependency detection from import statements
- Simple package installation
- 6 common package mappings
- Interactive confirmation prompts

---

[1.0.4]: https://github.com/Felixdiamond/pipwatch/releases/tag/v1.0.4
[1.0.0]: https://github.com/Felixdiamond/pipwatch/releases/tag/v1.0.0
[0.1.1]: https://github.com/Felixdiamond/pipwatch/releases/tag/v0.1.1
