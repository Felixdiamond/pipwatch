#!/usr/bin/env python3
"""Populate and manage mappings.json entries.

Two modes:
  add       - Manually add a mapping with PyPI validation
  discover  - Scan installed packages for import-name mismatches
"""

import argparse
import importlib.metadata
import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

MAPPINGS_PATH = Path(__file__).resolve().parent.parent / "src" / "pipwatch" / "mappings.json"


def normalize(name: str) -> str:
    """Normalize a package name for comparison (lowercase, hyphens to underscores)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def load_mappings() -> dict:
    """Load the current mappings.json file."""
    with open(MAPPINGS_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_mappings(data: dict) -> None:
    """Write mappings back to disk."""
    with open(MAPPINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def validate_pypi_package(package_name: str) -> bool:
    """Check if a package exists on PyPI."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        with urlopen(url, timeout=10) as resp:
            return resp.status == 200
    except (HTTPError, URLError, TimeoutError):
        return False
    except Exception:
        return False


def cmd_add(args: argparse.Namespace) -> None:
    """Add a single mapping to mappings.json."""
    import_name = args.import_name
    package_name = args.package_name
    category = args.category

    # Validate package on PyPI
    print(f"Checking if '{package_name}' exists on PyPI...")
    if not validate_pypi_package(package_name):
        print(f"ERROR: '{package_name}' was not found on PyPI.")
        print("Double-check the package name and try again.")
        sys.exit(1)
    print(f"  Found '{package_name}' on PyPI.")

    data = load_mappings()
    mappings = data.get("mappings", {})

    # Check for existing mapping
    if import_name in mappings:
        existing = mappings[import_name].get("package", "?")
        print(f"WARNING: '{import_name}' is already mapped to '{existing}'.")
        if not args.force:
            resp = input("Overwrite? [y/N] ").strip().lower()
            if resp != "y":
                print("Aborted.")
                return

    entry = {
        "package": package_name,
        "category": category,
        "verified": True,
    }

    if args.dry_run:
        print(f"\n[DRY RUN] Would add mapping:")
        print(f"  {import_name} -> {package_name} (category: {category})")
        return

    mappings[import_name] = entry
    data["mappings"] = dict(sorted(mappings.items()))
    save_mappings(data)
    print(f"Added: {import_name} -> {package_name} (category: {category})")


def cmd_discover(args: argparse.Namespace) -> None:
    """Discover import-name-to-package-name mismatches from installed packages."""
    data = load_mappings()
    existing = data.get("mappings", {})

    discoveries: list[tuple[str, str]] = []

    for dist in importlib.metadata.distributions():
        dist_name = dist.metadata["Name"]
        if not dist_name:
            continue

        # Get top-level import names
        top_level_text = dist.read_text("top_level.txt")
        if not top_level_text:
            continue

        import_names = [
            name.strip()
            for name in top_level_text.strip().splitlines()
            if name.strip() and not name.strip().startswith("_")
        ]

        for import_name in import_names:
            # Skip if import name matches the normalized package name
            if normalize(import_name) == normalize(dist_name):
                continue

            # Skip if already in mappings
            if import_name in existing:
                continue

            # Skip stdlib-like names
            if import_name in sys.stdlib_module_names:
                continue

            discoveries.append((import_name, dist_name))

    # Deduplicate
    seen = set()
    unique: list[tuple[str, str]] = []
    for imp, pkg in discoveries:
        if imp not in seen:
            seen.add(imp)
            unique.append((imp, pkg))

    if not unique:
        print("No new import-to-package mismatches found.")
        return

    unique.sort(key=lambda x: x[0].lower())

    print(f"Found {len(unique)} potential mapping(s):\n")
    print(f"  {'Import Name':<30} {'Package Name':<30}")
    print(f"  {'-' * 30} {'-' * 30}")
    for imp, pkg in unique:
        print(f"  {imp:<30} {pkg:<30}")

    if args.apply:
        if args.dry_run:
            print(f"\n[DRY RUN] Would add {len(unique)} mapping(s) to {MAPPINGS_PATH}")
            return

        mappings = data.get("mappings", {})
        added = 0
        for imp, pkg in unique:
            mappings[imp] = {
                "package": pkg,
                "category": "uncategorized",
                "verified": False,
            }
            added += 1

        data["mappings"] = dict(sorted(mappings.items()))
        save_mappings(data)
        print(f"\nAdded {added} mapping(s) to {MAPPINGS_PATH}")
        print("Review the entries and set appropriate categories and verified flags.")
    else:
        print(f"\nRun with --apply to add these to {MAPPINGS_PATH.name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage pipwatch package mappings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s add PIL pillow --category image-processing
  %(prog)s add sklearn scikit-learn --category data-science --dry-run
  %(prog)s discover
  %(prog)s discover --apply
        """,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add subcommand
    add_parser = subparsers.add_parser("add", help="Add a mapping manually")
    add_parser.add_argument("import_name", help="The import name (e.g. PIL, cv2, sklearn)")
    add_parser.add_argument("package_name", help="The PyPI package name (e.g. pillow, opencv-python)")
    add_parser.add_argument(
        "--category", default="uncategorized", help="Category for the mapping (default: uncategorized)"
    )
    add_parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    add_parser.add_argument("--force", action="store_true", help="Overwrite existing mapping without prompting")

    # discover subcommand
    discover_parser = subparsers.add_parser(
        "discover", help="Discover mappings from installed packages"
    )
    discover_parser.add_argument(
        "--apply", action="store_true", help="Write discovered mappings to mappings.json"
    )
    discover_parser.add_argument("--dry-run", action="store_true", help="Preview without writing")

    args = parser.parse_args()

    if not MAPPINGS_PATH.exists():
        print(f"ERROR: mappings file not found at {MAPPINGS_PATH}")
        print("Run this script from the project root.")
        sys.exit(1)

    if args.command == "add":
        cmd_add(args)
    elif args.command == "discover":
        cmd_discover(args)


if __name__ == "__main__":
    main()
