"""Tests for the mapping registry module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from pipwatch.mapping_registry import (
    MappingRegistry,
    get_registry,
    map_import_to_package,
)


class TestMappingRegistry:
    """Tests for MappingRegistry class."""

    def test_load_bundled_mappings(self):
        """Test loading mappings from bundled JSON file."""
        registry = MappingRegistry(use_cache=False)
        mappings = registry.load_mappings()

        # Should have loaded the bundled mappings
        assert isinstance(mappings, dict)
        assert len(mappings) > 0

        # Check some known mappings
        assert mappings.get("PIL") == "pillow"
        assert mappings.get("sklearn") == "scikit-learn"
        assert mappings.get("bs4") == "beautifulsoup4"

    def test_get_package_name(self):
        """Test getting package name for import."""
        registry = MappingRegistry(use_cache=False)

        assert registry.get_package_name("PIL") == "pillow"
        assert registry.get_package_name("cv2") == "opencv-python"
        assert registry.get_package_name("unknown_package") == "unknown_package"

    def test_get_version(self):
        """Test getting mapping version."""
        registry = MappingRegistry(use_cache=False)
        registry.load_mappings()
        version = registry.get_version()

        assert isinstance(version, str)
        assert version != "unknown"

    def test_get_stats(self):
        """Test getting mapping statistics."""
        registry = MappingRegistry(use_cache=False)
        stats = registry.get_stats()

        assert "total_mappings" in stats
        assert "version" in stats
        assert "cache_enabled" in stats
        assert stats["total_mappings"] > 0

    def test_cache_disabled(self):
        """Test that cache is not used when disabled."""
        registry = MappingRegistry(use_cache=False)
        mappings = registry.load_mappings()

        assert len(mappings) > 0
        # With cache disabled, cache file should not be created during load
        # (though it might exist from other tests)

    @patch("pipwatch.mapping_registry.urlopen")
    def test_load_from_url_success(self, mock_urlopen):
        """Test loading mappings from URL successfully."""
        # Mock successful URL fetch
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "version": "1.0.0",
                "mappings": {"test_import": {"package": "test-package", "category": "testing"}},
            }
        ).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        registry = MappingRegistry(use_cache=False)
        mappings = registry.load_mappings(force_refresh=True)

        assert "test_import" in mappings
        assert mappings["test_import"] == "test-package"

    @patch("pipwatch.mapping_registry.urlopen")
    def test_load_from_url_failure_fallback(self, mock_urlopen):
        """Test fallback to bundled mappings when URL fetch fails."""
        # Mock URL fetch failure
        mock_urlopen.side_effect = Exception("Network error")

        registry = MappingRegistry(use_cache=False)
        mappings = registry.load_mappings(force_refresh=True)

        # Should fall back to bundled mappings
        assert len(mappings) > 0
        assert "PIL" in mappings

    def test_clear_cache(self, tmp_path):
        """Test clearing the cache."""
        # Create a temporary cache file
        cache_file = tmp_path / "test_cache.json"
        cache_file.write_text('{"timestamp": 123456, "data": {}}')

        # Patch the CACHE_FILE constant
        with patch("pipwatch.mapping_registry.CACHE_FILE", cache_file):
            registry = MappingRegistry(use_cache=True)
            assert cache_file.exists()

            result = registry.clear_cache()

            assert result is True
            assert not cache_file.exists()

    def test_clear_cache_no_file(self):
        """Test clearing cache when no cache file exists."""
        registry = MappingRegistry(use_cache=True)

        # Ensure cache doesn't exist
        with patch("pipwatch.mapping_registry.CACHE_FILE") as mock_cache:
            mock_cache.exists.return_value = False
            result = registry.clear_cache()

            assert result is False


class TestGlobalRegistry:
    """Tests for global registry functions."""

    def test_get_registry_singleton(self):
        """Test that get_registry returns the same instance."""
        registry1 = get_registry()
        registry2 = get_registry()

        assert registry1 is registry2

    def test_map_import_to_package_function(self):
        """Test the convenience function."""
        result = map_import_to_package("PIL")
        assert result == "pillow"

        result = map_import_to_package("unknown")
        assert result == "unknown"


class TestMappingFormat:
    """Tests for mapping file format."""

    def test_bundled_mappings_format(self):
        """Test that bundled mappings file has correct format."""
        registry = MappingRegistry(use_cache=False)
        bundled_path = registry._get_bundled_mappings_path()

        assert bundled_path.exists()

        with open(bundled_path) as f:
            data = json.load(f)

        # Check required fields
        assert "version" in data
        assert "mappings" in data
        assert isinstance(data["mappings"], dict)

        # Check mapping structure
        for import_name, mapping_data in data["mappings"].items():
            assert isinstance(import_name, str)
            assert isinstance(mapping_data, dict)
            assert "package" in mapping_data
            assert "category" in mapping_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
