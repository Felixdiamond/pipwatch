import sys
from pathlib import Path

import pytest

# Make the src package importable without pip install -e
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pipwatch.mapping_registry as mr


@pytest.fixture(autouse=True)
def reset_global_registry():
    """Reset the global registry singleton between tests."""
    yield
    mr._global_registry = None
