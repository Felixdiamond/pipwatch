"""
Package mapping registry for Pipwatch.

This module handles loading, caching, and managing import-to-package mappings
from various sources (local file, GitHub, cache).
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Default GitHub URL for the mappings file
DEFAULT_MAPPINGS_URL = (
    "https://raw.githubusercontent.com/Felixdiamond/pipwatch/"
    "main/src/pipwatch/mappings.json"
)

# Cache settings
CACHE_DIR = Path.home() / ".pipwatch"
CACHE_FILE = CACHE_DIR / "mappings_cache.json"
CACHE_TTL = 86400  # 24 hours in seconds


class MappingRegistry:
    """Registry for managing import-to-package name mappings."""

    def __init__(self, use_cache: bool = True, remote_url: Optional[str] = None):
        """
        Initialize the mapping registry.

        Args:
            use_cache: Whether to use cached mappings
            remote_url: Custom URL for fetching remote mappings
        """
        self.use_cache = use_cache
        self.remote_url = remote_url or DEFAULT_MAPPINGS_URL
        self._mappings: Optional[Dict[str, str]] = None
        self._metadata: Optional[Dict] = None

    def _get_bundled_mappings_path(self) -> Path:
        """Get the path to the bundled mappings.json file."""
        return Path(__file__).parent / "mappings.json"

    def _load_from_file(self, file_path: Path) -> Dict:
        """Load mappings from a JSON file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
                logging.debug(f"Loaded mappings from {file_path}")
                return data
        except Exception as e:
            logging.error(f"Failed to load mappings from {file_path}: {e}")
            return {}

    def _load_from_url(self, url: str, timeout: int = 5) -> Optional[Dict]:
        """
        Load mappings from a remote URL.

        Args:
            url: URL to fetch mappings from
            timeout: Request timeout in seconds

        Returns:
            Loaded mappings data or None if failed
        """
        try:
            logging.debug(f"Fetching mappings from {url}")
            req = Request(url, headers={"User-Agent": "Pipwatch/1.0"})
            with urlopen(req, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
                logging.debug("Fetched mappings from remote")
                return data
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in remote mappings: {e}")
            return None
        except (URLError, HTTPError, TimeoutError) as e:
            logging.debug(f"Failed to fetch remote mappings: {e}")
            return None
        except Exception as e:
            logging.debug(f"Unexpected error fetching remote mappings: {e}")
            return None

    def _save_to_cache(self, data: Dict) -> None:
        """Save mappings data to cache file."""
        if not self.use_cache:
            return

        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_data = {"timestamp": time.time(), "data": data}
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)
            logging.debug(f"Saved mappings to cache: {CACHE_FILE}")
        except Exception as e:
            logging.debug(f"Failed to save cache: {e}")

    def _load_from_cache(self) -> Optional[Dict]:
        """Load mappings from cache if valid."""
        if not self.use_cache or not CACHE_FILE.exists():
            return None

        try:
            with open(CACHE_FILE, encoding="utf-8") as f:
                cache_data = json.load(f)

            # Check if cache is still valid
            timestamp = cache_data.get("timestamp", 0)
            age = time.time() - timestamp

            if age < CACHE_TTL:
                logging.debug(f"Using cached mappings (age: {int(age/3600)}h)")
                return cache_data.get("data")
            else:
                logging.debug(f"Cache expired (age: {int(age/3600)}h)")
                return None
        except Exception as e:
            logging.debug(f"Failed to load cache: {e}")
            return None

    def _parse_mappings(self, data: Dict) -> Dict[str, str]:
        """
        Parse mappings data into a simple import->package dictionary.

        Args:
            data: Raw mappings data from JSON

        Returns:
            Dictionary mapping import names to package names
        """
        mappings = {}
        raw_mappings = data.get("mappings", {})

        for import_name, mapping_data in raw_mappings.items():
            if isinstance(mapping_data, dict):
                package = mapping_data.get("package", import_name)
            else:
                # Fallback for simple string mappings
                package = mapping_data
            mappings[import_name] = package

        return mappings

    def load_mappings(self, force_refresh: bool = False) -> Dict[str, str]:
        """
        Load mappings from available sources with fallback chain.

        Priority:
        1. Remote URL (if not cached or force_refresh)
        2. Cache (if valid and not force_refresh)
        3. Bundled mappings.json

        Args:
            force_refresh: Force fetching from remote even if cache is valid

        Returns:
            Dictionary of import name to package name mappings
        """
        if self._mappings is not None and not force_refresh:
            return self._mappings

        data = None

        # Try loading from cache first (unless forcing refresh)
        if not force_refresh:
            data = self._load_from_cache()
            if data:
                self._metadata = data
                self._mappings = self._parse_mappings(data)
                return self._mappings

        # Try fetching from remote
        remote_data = self._load_from_url(self.remote_url)
        if remote_data:
            data = remote_data
            self._save_to_cache(data)

        # Fallback to bundled mappings
        if not data:
            bundled_path = self._get_bundled_mappings_path()
            if bundled_path.exists():
                data = self._load_from_file(bundled_path)
                logging.debug("Using bundled mappings")
            else:
                logging.warning("No mappings file found!")
                data = {}

        self._metadata = data
        self._mappings = self._parse_mappings(data)
        return self._mappings

    def get_package_name(self, import_name: str) -> str:
        """
        Get the PyPI package name for an import name.

        Args:
            import_name: The import name to look up

        Returns:
            Package name, or the import name itself if no mapping exists
        """
        mappings = self.load_mappings()
        return mappings.get(import_name, import_name)

    def get_version(self) -> str:
        """Get the version of the loaded mappings."""
        if self._metadata:
            return self._metadata.get("version", "unknown")
        return "unknown"

    def get_stats(self) -> Dict:
        """Get statistics about the loaded mappings."""
        mappings = self.load_mappings()
        stats = {
            "total_mappings": len(mappings),
            "version": self.get_version(),
            "cache_enabled": self.use_cache,
            "cache_location": str(CACHE_FILE) if self.use_cache else "N/A",
        }

        if self._metadata:
            stats["last_updated"] = self._metadata.get("last_updated", "unknown")

        return stats

    def clear_cache(self) -> bool:
        """
        Clear the cached mappings.

        Returns:
            True if cache was cleared, False otherwise
        """
        try:
            if CACHE_FILE.exists():
                CACHE_FILE.unlink()
                logging.debug("Cache file removed")
                return True
            else:
                logging.debug("No cache file found")
                return False
        except Exception as e:
            logging.error(f"Failed to clear cache: {e}")
            return False


# Global registry instance
_global_registry: Optional[MappingRegistry] = None


def get_registry(
    use_cache: bool = True, remote_url: Optional[str] = None
) -> MappingRegistry:
    """
    Get or create the global mapping registry instance.

    Args:
        use_cache: Whether to use cached mappings
        remote_url: Custom URL for remote mappings

    Returns:
        Global MappingRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = MappingRegistry(use_cache=use_cache, remote_url=remote_url)
    return _global_registry


def map_import_to_package(import_name: str) -> str:
    """
    Map an import name to its PyPI package name.

    This is a convenience function that uses the global registry.

    Args:
        import_name: The import name to look up

    Returns:
        The PyPI package name
    """
    registry = get_registry()
    return registry.get_package_name(import_name)
