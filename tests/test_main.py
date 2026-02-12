"""Tests for pipwatch main module."""

import pytest

from pipwatch.main import (
    analyze_file_content,
    extract_imports,
    filter_standard_library,
    generate_requirements_file,
    get_installed_packages,
    map_import_to_package,
)


class TestExtractImports:
    """Test import extraction functionality."""

    def test_basic_imports(self, tmp_path):
        """Test extracting basic import statements."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
import os
import sys
import requests
from flask import Flask
""")
        imports = extract_imports(str(test_file))
        assert "os" in imports
        assert "sys" in imports
        assert "requests" in imports
        assert "flask" in imports

    def test_nested_imports(self, tmp_path):
        """Test extracting nested module imports."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
from package.subpackage import module
import package.subpackage.module
""")
        imports = extract_imports(str(test_file))
        assert "package" in imports

    def test_syntax_error_handling(self, tmp_path):
        """Test handling of files with syntax errors."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
import os
def broken(
""")
        imports = extract_imports(str(test_file))
        assert imports == set()

    def test_empty_file(self, tmp_path):
        """Test extracting from empty file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("")
        imports = extract_imports(str(test_file))
        assert imports == set()


class TestFilterStandardLibrary:
    """Test standard library filtering."""

    def test_filter_stdlib(self):
        """Test filtering out standard library modules."""
        imports = {"os", "sys", "requests", "json", "numpy"}
        filtered = filter_standard_library(imports)
        assert "os" not in filtered
        assert "sys" not in filtered
        assert "json" not in filtered
        assert "requests" in filtered
        assert "numpy" in filtered

    def test_all_stdlib(self):
        """Test with only standard library imports."""
        imports = {"os", "sys", "json", "pathlib"}
        filtered = filter_standard_library(imports)
        assert len(filtered) == 0

    def test_all_third_party(self):
        """Test with only third-party imports."""
        imports = {"requests", "numpy", "flask"}
        filtered = filter_standard_library(imports)
        assert filtered == imports


class TestMapImportToPackage:
    """Test import to package name mapping."""

    def test_common_mappings(self):
        """Test well-known package mappings."""
        assert map_import_to_package("PIL") == "pillow"
        assert map_import_to_package("cv2") == "opencv-python"
        assert map_import_to_package("sklearn") == "scikit-learn"
        assert map_import_to_package("bs4") == "beautifulsoup4"
        assert map_import_to_package("yaml") == "pyyaml"

    def test_direct_mapping(self):
        """Test imports that map directly to package names."""
        assert map_import_to_package("requests") == "requests"
        assert map_import_to_package("numpy") == "numpy"
        assert map_import_to_package("pandas") == "pandas"

    def test_database_mappings(self):
        """Test database-related mappings."""
        assert map_import_to_package("psycopg2") == "psycopg2-binary"
        assert map_import_to_package("MySQLdb") == "mysqlclient"

    def test_crypto_mappings(self):
        """Test cryptography-related mappings."""
        assert map_import_to_package("Crypto") == "pycryptodome"
        assert map_import_to_package("jwt") == "PyJWT"


class TestAnalyzeFileContent:
    """Test file content analysis."""

    def test_pip_install_comments(self, tmp_path):
        """Test detecting pip install comments."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
# pip install requests
# pip install numpy>=1.20.0
import os
""")
        packages, req_mentioned = analyze_file_content(str(test_file))
        assert "requests" in packages
        assert "numpy>=1.20.0" in packages
        assert not req_mentioned

    def test_requirements_txt_mention(self, tmp_path):
        """Test detecting requirements.txt mentions."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
# Install dependencies from requirements.txt
import os
""")
        packages, req_mentioned = analyze_file_content(str(test_file))
        assert req_mentioned

    def test_no_special_content(self, tmp_path):
        """Test file with no special content."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
import os
print("Hello")
""")
        packages, req_mentioned = analyze_file_content(str(test_file))
        assert len(packages) == 0
        assert not req_mentioned


class TestGenerateRequirementsFile:
    """Test requirements.txt generation."""

    def test_generate_requirements(self, tmp_path):
        """Test generating a requirements file."""
        output_file = tmp_path / "requirements.txt"
        dependencies = {"requests", "numpy", "bs4", "pandas"}

        generate_requirements_file(dependencies, str(output_file))

        assert output_file.exists()
        content = output_file.read_text()
        assert "beautifulsoup4" in content  # bs4 should be mapped
        assert "numpy" in content
        assert "pandas" in content
        assert "requests" in content

    def test_generate_sorted_requirements(self, tmp_path):
        """Test that requirements are sorted alphabetically."""
        output_file = tmp_path / "requirements.txt"
        dependencies = {"zebra", "apple", "banana"}

        generate_requirements_file(dependencies, str(output_file))

        lines = output_file.read_text().strip().split("\n")
        assert lines == sorted(lines)

    def test_generate_empty_requirements(self, tmp_path):
        """Test generating requirements with no dependencies."""
        output_file = tmp_path / "requirements.txt"
        dependencies = set()

        generate_requirements_file(dependencies, str(output_file))

        # Should not create file for empty dependencies - verify this
        assert not output_file.exists()


class TestGetInstalledPackages:
    """Test getting installed packages."""

    def test_get_installed_packages(self):
        """Test that we can retrieve installed packages."""
        packages = get_installed_packages()
        assert isinstance(packages, set)
        # pip should always be installed
        assert any("pip" in pkg for pkg in packages)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
