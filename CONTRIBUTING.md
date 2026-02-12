# Contributing to Pipwatch

Guidelines for contributing to Pipwatch.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Commit Messages](#commit-messages)

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow:

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on what's best for the community
- Show empathy towards other community members

## How Can I Contribute?

### Reporting Bugs

Before creating a bug report, please check existing issues to avoid duplicates.

When filing a bug report, include:
- **Clear title and description**
- **Steps to reproduce** the issue
- **Expected behavior** vs actual behavior
- **Python version** and operating system
- **Code samples** or test cases if applicable

### Suggesting Features

Feature suggestions are welcome. Please:
- **Use a clear title** that describes the feature
- **Explain the use case** - why would this be useful?
- **Describe the proposed solution**
- **Consider alternatives** you've thought about

### Adding Package Mappings

One of the easiest ways to contribute is adding new package mappings.

If you find an import that doesn't map correctly to its PyPI package:

1. Edit `src/pipwatch/mappings.json`
2. Add a mapping entry:
   ```json
   "import_name": {
     "package": "pypi-package-name",
     "category": "category-name",
     "verified": true
   }
   ```
3. Add a test in `tests/test_mapping_registry.py`
4. Submit a pull request

See [docs/CONTRIBUTING_MAPPINGS.md](docs/CONTRIBUTING_MAPPINGS.md) for full details.

### Improving Documentation

Documentation improvements are always appreciated:
- Fix typos or unclear explanations
- Add examples
- Improve API documentation

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git

### Setup Instructions

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR-USERNAME/pipwatch.git
   cd pipwatch
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

5. **Verify setup**
   ```bash
   pytest tests/
   ```

## Pull Request Process

1. **Create a new branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write code following our [coding standards](#coding-standards)
   - Add tests for new functionality
   - Update documentation as needed

3. **Run tests and linting**
   ```bash
   # Run tests
   pytest tests/

   # Format code
   black src/ tests/
   isort src/ tests/

   # Lint
   ruff check src/ tests/ --fix

   # Type check
   mypy src/
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```
   See [commit message guidelines](#commit-messages) below.

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then open a pull request on GitHub.

6. **PR Review**
   - Address any feedback from reviewers
   - Keep the PR focused on a single feature/fix
   - Ensure CI passes

## Coding Standards

### Python Style

We follow PEP 8 with some modifications:

- **Line length**: 100 characters (not 79)
- **Formatter**: Black
- **Import sorting**: isort with Black profile
- **Linter**: Ruff

### Code Organization

- **Type hints**: Use type hints for all function signatures
- **Docstrings**: Use Google-style docstrings
- **Naming**:
  - `snake_case` for functions and variables
  - `PascalCase` for classes
  - `UPPER_CASE` for constants

Example:
```python
def map_import_to_package(import_name: str) -> str:
    """Map import names to their PyPI package names.

    Args:
        import_name: The import name as it appears in code

    Returns:
        The corresponding PyPI package name

    Example:
        >>> map_import_to_package('PIL')
        'pillow'
    """
    mappings = {...}
    return mappings.get(import_name, import_name)
```

## Testing

### Writing Tests

- **Test file naming**: `test_*.py`
- **Test class naming**: `Test*`
- **Test function naming**: `test_*`
- **Use fixtures**: For common setup/teardown
- **Use tmp_path**: For file system tests

Example:
```python
def test_extract_imports(tmp_path):
    """Test extracting basic import statements."""
    test_file = tmp_path / "test.py"
    test_file.write_text("import requests\nimport numpy")

    imports = extract_imports(str(test_file))

    assert 'requests' in imports
    assert 'numpy' in imports
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src/pipwatch

# Run specific test
pytest tests/test_main.py::TestExtractImports::test_basic_imports

# Run with verbose output
pytest tests/ -v

# Run and stop at first failure
pytest tests/ -x
```

## Commit Messages

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

### Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples
```
feat(mappings): add support for Django REST framework

Add package mapping for 'rest_framework' -> 'djangorestframework'

Closes #123
```

```
fix(parser): handle syntax errors gracefully

Previously, syntax errors would crash the program. Now they're
caught and logged, allowing the program to continue.
```

```
docs(readme): add installation instructions for pip
```

## Getting Help

- **GitHub Discussions** - Ask questions and discuss ideas
- **GitHub Issues** - Report bugs and request features

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
