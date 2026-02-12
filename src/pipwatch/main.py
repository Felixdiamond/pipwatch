import argparse
import ast
import importlib.metadata
import logging
import re
import subprocess
import sys
from pathlib import Path

from .mapping_registry import get_registry
from .mapping_registry import map_import_to_package as registry_map


def setup_logging(verbose: bool = False) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def find_python_files(path: Path) -> list[Path]:
    """Find all Python files in a directory recursively."""
    if path.is_file():
        return [path]

    if path.is_dir():
        skip_dirs = {
            ".venv",
            "venv",
            "env",
            ".env",
            "node_modules",
            ".git",
            "__pycache__",
            ".tox",
            "build",
            "dist",
            ".eggs",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
        }

        python_files = []
        for py_file in path.rglob("*.py"):
            if not any(part in skip_dirs for part in py_file.parts):
                python_files.append(py_file)

        logging.debug(f"Found {len(python_files)} Python files in {path}")
        return python_files

    return []


def extract_imports(file_path: str) -> set[str]:
    """Extract all import statements from a Python file."""
    logging.debug(f"Extracting imports from {file_path}")
    try:
        with open(file_path, encoding="utf-8") as file:
            tree = ast.parse(file.read(), filename=file_path)
    except SyntaxError as e:
        logging.error(f"Syntax error in {file_path}: {e}")
        return set()
    except Exception as e:
        logging.error(f"Error reading {file_path}: {e}")
        return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])

    logging.debug(f"Found {len(imports)} imports: {imports}")
    return imports


def filter_standard_library(imports: set[str]) -> set[str]:
    """Filter out standard library modules from imports."""
    standard_libs = set(sys.stdlib_module_names)
    third_party = {imp for imp in imports if imp not in standard_libs}
    logging.debug(f"Filtered to {len(third_party)} third-party imports")
    return third_party


def get_installed_packages() -> set[str]:
    """Get a set of all installed package names."""
    try:
        installed = {
            dist.metadata["Name"].lower().replace("_", "-")
            for dist in importlib.metadata.distributions()
        }
        logging.debug(f"Found {len(installed)} installed packages")
        return installed
    except Exception as e:
        logging.warning(f"Error getting installed packages: {e}")
        return set()


def map_import_to_package(import_name: str) -> str:
    """Map an import name to its PyPI package name.

    Uses the mapping registry. Returns the import name unchanged
    if no mapping exists.
    """
    return registry_map(import_name)


def install_dependencies(dependencies: set[str], dry_run: bool = False) -> None:
    """Install missing dependencies with progress indicators.

    Args:
        dependencies: Set of package names to install
        dry_run: If True, only show what would be installed without installing
    """
    installed = get_installed_packages()
    to_install = []

    for dep in dependencies:
        package_name = map_import_to_package(dep)
        # Normalize package name for comparison
        normalized_pkg = package_name.lower().replace("_", "-")
        if normalized_pkg not in installed:
            to_install.append(package_name)
        else:
            logging.debug(f"{package_name} is already installed")

    if not to_install:
        logging.info("✓ All dependencies are already installed.")
        return

    logging.info(f"\nPackages to install: {', '.join(to_install)}")

    if dry_run:
        logging.info("\n[DRY RUN] Would install the following packages:")
        for dep in to_install:
            logging.info(f"  • {dep}")
        return

    failed = []
    suppress_output = not logging.getLogger().isEnabledFor(logging.DEBUG)
    for i, dep in enumerate(to_install, 1):
        logging.info(f"\n[{i}/{len(to_install)}] Installing {dep}...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", dep, "-q"],
                stdout=subprocess.DEVNULL if suppress_output else None,
            )
            logging.info(f"✓ Successfully installed {dep}")
        except subprocess.CalledProcessError:
            logging.error(f"✗ Failed to install {dep}")
            failed.append(dep)

    if failed:
        logging.warning(f"\nFailed to install: {', '.join(failed)}")
        logging.warning(
            "These packages might not be available on PyPI or there could be a naming mismatch."
        )
    else:
        logging.info("\n✓ All dependencies installed successfully!")


def analyze_file_content(file_path: str) -> tuple[list[str], bool]:
    """Analyze file content for pip install comments and requirements.txt references.

    Args:
        file_path: Path to the Python file

    Returns:
        Tuple of (list of packages from comments, whether requirements.txt is mentioned)
    """
    try:
        with open(file_path, encoding="utf-8") as file:
            content = file.read()
    except Exception as e:
        logging.error(f"Error reading file: {e}")
        return [], False

    # Look for pip install comments with optional version specifiers
    # Matches: # pip install package, # pip install package>=1.0, etc.
    pip_installs = re.findall(r"#\s*pip install\s+([\w\-\[\]<>=.,]+)", content)

    # Look for requirements.txt references
    req_file_mention = re.search(r"#.*requirements\.txt", content)

    logging.debug(f"Found {len(pip_installs)} pip install comments")
    return pip_installs, bool(req_file_mention)


def generate_requirements_file(
    dependencies: set[str], output_path: str = "requirements.txt"
) -> None:
    """Generate a requirements.txt file from detected dependencies.

    Args:
        dependencies: Set of package names
        output_path: Path where to save the requirements file
    """
    if not dependencies:
        logging.warning("No dependencies to write to requirements file.")
        return

    packages = sorted([map_import_to_package(dep) for dep in dependencies])

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            for package in packages:
                f.write(f"{package}\n")
        logging.info(f"✓ Generated {output_path} with {len(packages)} packages")
    except Exception as e:
        logging.error(f"Failed to write requirements file: {e}")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Automatically detect and install Python dependencies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s script.py                    # Analyze single file and install dependencies
  %(prog)s .                            # Analyze all Python files in current directory
  %(prog)s myfolder/                    # Analyze all Python files in a folder
  %(prog)s script.py --dry-run          # Show what would be installed
  %(prog)s script.py --generate         # Generate requirements.txt
  %(prog)s script.py --verbose          # Show detailed logging
  %(prog)s script.py --yes              # Auto-confirm installation

Mapping Management:
  %(prog)s --update-mappings            # Update package mappings from GitHub
  %(prog)s --clear-cache                # Clear cached mappings
  %(prog)s --show-mappings              # Show mapping statistics
        """,
    )

    parser.add_argument(
        "file_path", nargs="?", help="Path to a Python file or directory to analyze"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be installed without actually installing",
    )

    parser.add_argument(
        "--generate",
        "-g",
        action="store_true",
        help="Generate requirements.txt from detected dependencies",
    )

    parser.add_argument(
        "--output",
        "-o",
        default="requirements.txt",
        help="Output path for generated requirements file (default: requirements.txt)",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Automatically confirm installation without prompting",
    )

    # Mapping management commands
    parser.add_argument(
        "--update-mappings",
        action="store_true",
        help="Update package mappings from remote source (GitHub)",
    )

    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cached package mappings",
    )

    parser.add_argument(
        "--show-mappings",
        action="store_true",
        help="Show statistics about loaded package mappings",
    )

    parser.add_argument("--version", action="version", version="%(prog)s 1.0.4")

    return parser.parse_args()


def main():
    """Main entry point for pipwatch."""
    args = parse_args()
    setup_logging(args.verbose)

    # Handle mapping management commands
    if args.update_mappings:
        logging.info("Updating package mappings from remote source...")
        registry = get_registry()
        registry.load_mappings(force_refresh=True)
        stats = registry.get_stats()
        logging.info("✓ Mappings updated successfully!")
        logging.info(f"  Version: {stats['version']}")
        logging.info(f"  Total mappings: {stats['total_mappings']}")
        logging.info(f"  Last updated: {stats.get('last_updated', 'unknown')}")
        return

    if args.clear_cache:
        logging.info("Clearing cached mappings...")
        registry = get_registry()
        if registry.clear_cache():
            logging.info("✓ Cache cleared successfully")
        else:
            logging.info("No cache to clear")
        return

    if args.show_mappings:
        logging.info("Loading package mapping statistics...")
        registry = get_registry()
        stats = registry.get_stats()
        logging.info("\n📊 Package Mapping Statistics:")
        logging.info(f"  Version: {stats['version']}")
        logging.info(f"  Total mappings: {stats['total_mappings']}")
        logging.info(f"  Last updated: {stats.get('last_updated', 'unknown')}")
        logging.info(f"  Cache enabled: {stats['cache_enabled']}")
        logging.info(f"  Cache location: {stats['cache_location']}")
        return

    # Require file_path for analysis commands
    if not args.file_path:
        logging.error("Error: file_path is required for analysis")
        logging.info("Use --help for usage information")
        sys.exit(1)

    path = Path(args.file_path)

    if not path.exists():
        logging.error(f"Path not found: {args.file_path}")
        sys.exit(1)

    python_files = find_python_files(path)

    if not python_files:
        logging.error(f"No Python files found in {args.file_path}")
        sys.exit(1)

    if len(python_files) == 1:
        logging.info(f"Analyzing {python_files[0]}...")
    else:
        logging.info(f"Analyzing {len(python_files)} Python files in {args.file_path}...")

    all_deps = set()
    all_pip_installs = []
    req_file_mentioned = False

    for file_path in python_files:
        imports = extract_imports(str(file_path))
        third_party_imports = filter_standard_library(imports)
        pip_installs, req_mention = analyze_file_content(str(file_path))

        all_deps.update(third_party_imports)
        all_pip_installs.extend(pip_installs)
        req_file_mentioned = req_file_mentioned or req_mention

    all_deps.update(all_pip_installs)

    if all_deps:
        logging.info(f"\nDetected {len(all_deps)} unique dependencies total.")

    if not all_deps and not req_file_mentioned:
        logging.info("✓ No third-party dependencies found.")
        return

    if all_deps:
        logging.info("\nFound the following dependencies:")
        for dep in sorted(all_deps):
            pkg = map_import_to_package(dep)
            if pkg != dep:
                logging.info(f"  • {dep} → {pkg}")
            else:
                logging.info(f"  • {dep}")

    # Handle requirements.txt mention
    if req_file_mentioned:
        logging.info("\nℹ A reference to 'requirements.txt' was found in the file.")
        if not args.yes:
            user_input = input(
                "Do you want to install dependencies from 'requirements.txt'? (y/n): "
            )
        else:
            user_input = "y"

        if user_input.lower() == "y":
            try:
                logging.info("Installing from requirements.txt...")
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
                )
                logging.info("✓ Dependencies from requirements.txt installed successfully!")
            except subprocess.CalledProcessError:
                logging.error(
                    "✗ Failed to install from requirements.txt. "
                    "The file might not exist or there could be an error."
                )
            except FileNotFoundError:
                logging.error("✗ requirements.txt file not found.")

    # Generate mode
    if args.generate:
        generate_requirements_file(all_deps, args.output)
        return

    # Install mode
    if args.dry_run:
        install_dependencies(all_deps, dry_run=True)
    else:
        if not args.yes and all_deps:
            user_input = input("\nDo you want to install the detected dependencies? (y/n): ")
        else:
            user_input = "y"

        if user_input.lower() == "y":
            install_dependencies(all_deps, dry_run=False)
        else:
            logging.info("Installation cancelled.")


if __name__ == "__main__":
    main()
