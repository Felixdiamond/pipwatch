#!/usr/bin/env python3
"""Fetch import-to-package mappings from PyPI.

Two modes:
  fetch  - Pull package list from PyPI and build a mappings JSON file
  apply  - Merge a generated mappings JSON into the main mappings.json
"""

from __future__ import annotations

import argparse
import html
import io
import json
import re
import sys
import time
import zipfile
from datetime import date
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MAPPINGS_PATH = Path(__file__).resolve().parent.parent / "src" / "pipwatch" / "mappings.json"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "pypi_mappings.json"
SIMPLE_INDEX_URL = "https://pypi.org/simple/"
USER_AGENT = "pipwatch-mappings-fetcher/1.0 (+https://github.com/Felixdiamond/pipwatch)"


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def fetch_url(url: str, timeout: int, retries: int) -> bytes:
    last_err: Exception | None = None
    for _ in range(retries + 1):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            last_err = exc
            time.sleep(0.5)
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def load_simple_index(cache_path: Path | None, refresh: bool, timeout: int, retries: int) -> str:
    if cache_path and cache_path.exists() and not refresh:
        return cache_path.read_text(encoding="utf-8")

    content = fetch_url(SIMPLE_INDEX_URL, timeout=timeout, retries=retries).decode("utf-8")
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(content, encoding="utf-8")
    return content


def parse_simple_index(html_text: str) -> list[str]:
    names = re.findall(r">([^<]+)</a>", html_text)
    cleaned = [html.unescape(name).strip() for name in names]
    return [name for name in cleaned if name]


def filter_names(
    names: Iterable[str],
    starts_with: list[str],
    offset: int,
    limit: int | None,
) -> list[str]:
    lowered = [n.strip() for n in names if n.strip()]
    if starts_with:
        prefixes = tuple(p.lower() for p in starts_with)
        lowered = [n for n in lowered if n.lower().startswith(prefixes)]
    lowered.sort(key=str.lower)
    if offset:
        lowered = lowered[offset:]
    if limit is not None:
        lowered = lowered[:limit]
    return lowered


def choose_wheel(urls: list[dict]) -> dict | None:
    wheels = [u for u in urls if u.get("packagetype") == "bdist_wheel" and not u.get("yanked")]
    if not wheels:
        return None

    def score(w: dict) -> tuple[int, int]:
        filename = w.get("filename", "")
        is_py3_any = 0
        if "py3-none-any" in filename:
            is_py3_any = 2
        elif "py2.py3-none-any" in filename:
            is_py3_any = 1
        size = w.get("size") or 0
        return (-is_py3_any, size)

    return sorted(wheels, key=score)[0]


def read_top_level_from_wheel(data: bytes) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = [n for n in zf.namelist() if n.endswith(".dist-info/top_level.txt")]
        if not names:
            return []
        with zf.open(names[0]) as f:
            content = f.read().decode("utf-8", errors="replace")
    return [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("_")]


def fetch_top_level_names(
    package_name: str,
    timeout: int,
    retries: int,
    max_wheel_bytes: int,
) -> list[str]:
    meta = json.loads(fetch_url(f"https://pypi.org/pypi/{package_name}/json", timeout, retries))
    urls = meta.get("urls", [])
    wheel = choose_wheel(urls)
    if not wheel:
        return []
    size = wheel.get("size") or 0
    if size and size > max_wheel_bytes:
        return []
    wheel_url = wheel.get("url")
    if not wheel_url:
        return []
    data = fetch_url(wheel_url, timeout, retries)
    return read_top_level_from_wheel(data)


def cmd_fetch(args: argparse.Namespace) -> None:
    if not MAPPINGS_PATH.exists():
        print(f"ERROR: mappings file not found at {MAPPINGS_PATH}")
        sys.exit(1)

    mappings_data = load_json(MAPPINGS_PATH)
    existing = mappings_data.get("mappings", {})
    existing_keys = set(existing.keys())

    index_text = load_simple_index(args.index_cache, args.refresh_index, args.timeout, args.retries)
    names = parse_simple_index(index_text)
    names = filter_names(names, args.starts_with, args.offset, args.limit)

    if not names:
        print("No packages matched the filters.")
        return

    max_wheel_bytes = int(args.max_wheel_mb * 1024 * 1024)
    results: dict[str, dict] = {}
    skipped = 0

    for idx, package_name in enumerate(names, 1):
        try:
            import_names = fetch_top_level_names(
                package_name=package_name,
                timeout=args.timeout,
                retries=args.retries,
                max_wheel_bytes=max_wheel_bytes,
            )
        except Exception:
            skipped += 1
            if args.verbose:
                print(f"Skip {package_name}: failed to fetch metadata")
            time.sleep(args.sleep)
            continue

        for import_name in import_names:
            if normalize(import_name) == normalize(package_name):
                continue
            if import_name in existing_keys:
                continue
            if import_name in results:
                continue
            if import_name in sys.stdlib_module_names:
                continue
            results[import_name] = {
                "package": package_name,
                "category": "uncategorized",
                "verified": False,
            }

        if args.verbose and idx % 50 == 0:
            print(f"Processed {idx}/{len(names)} packages")
        time.sleep(args.sleep)

    output = {
        "generated_at": date.today().isoformat(),
        "source": "pypi-simple",
        "package_count": len(names),
        "mapping_count": len(results),
        "mappings": dict(sorted(results.items())),
    }

    if args.dry_run:
        print(f"[DRY RUN] Would write {len(results)} mappings to {args.output}")
        return

    save_json(args.output, output)
    print(f"Wrote {len(results)} mappings to {args.output}")


def cmd_apply(args: argparse.Namespace) -> None:
    if not MAPPINGS_PATH.exists():
        print(f"ERROR: mappings file not found at {MAPPINGS_PATH}")
        sys.exit(1)

    if not args.input.exists():
        print(f"ERROR: input file not found at {args.input}")
        sys.exit(1)

    data = load_json(MAPPINGS_PATH)
    mappings = data.get("mappings", {})
    incoming = load_json(args.input).get("mappings", {})

    added = 0
    skipped = 0
    for import_name, entry in incoming.items():
        if import_name in mappings and not args.overwrite:
            skipped += 1
            continue
        mappings[import_name] = {
            "package": entry.get("package"),
            "category": entry.get("category", "uncategorized"),
            "verified": bool(entry.get("verified", False)),
        }
        added += 1

    if added:
        data["mappings"] = dict(sorted(mappings.items()))
        data["last_updated"] = date.today().isoformat()

    if args.dry_run:
        print(f"[DRY RUN] Would add {added} mappings, skip {skipped}")
        return

    if added:
        save_json(MAPPINGS_PATH, data)
    print(f"Added {added} mappings, skipped {skipped}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch and apply import-to-package mappings from PyPI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s fetch --starts-with a --limit 500
  %(prog)s fetch --starts-with numpy --limit 50 --output scripts/pypi_mappings.json
  %(prog)s apply --input scripts/pypi_mappings.json
        """,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch mappings from PyPI")
    fetch_parser.add_argument("--starts-with", action="append", default=[], help="Prefix filter")
    fetch_parser.add_argument("--offset", type=int, default=0, help="Skip first N packages")
    fetch_parser.add_argument("--limit", type=int, default=None, help="Limit number of packages")
    fetch_parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON file")
    fetch_parser.add_argument("--index-cache", type=Path, default=None, help="Cache path for PyPI index")
    fetch_parser.add_argument("--refresh-index", action="store_true", help="Refresh PyPI index cache")
    fetch_parser.add_argument("--sleep", type=float, default=0.2, help="Delay between packages")
    fetch_parser.add_argument("--timeout", type=int, default=15, help="Network timeout in seconds")
    fetch_parser.add_argument("--retries", type=int, default=2, help="Retry count for network calls")
    fetch_parser.add_argument("--max-wheel-mb", type=float, default=5.0, help="Skip wheels larger than this")
    fetch_parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    fetch_parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    apply_parser = subparsers.add_parser("apply", help="Apply mappings to mappings.json")
    apply_parser.add_argument("--input", type=Path, default=DEFAULT_OUTPUT, help="Input JSON file")
    apply_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing mappings")
    apply_parser.add_argument("--dry-run", action="store_true", help="Preview without writing")

    args = parser.parse_args()
    if args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "apply":
        cmd_apply(args)


if __name__ == "__main__":
    main()
