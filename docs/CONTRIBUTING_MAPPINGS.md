# Contributing Package Mappings

## Overview

Package name mappings are stored in `mappings.json`. You can add new mappings by editing this file and submitting a pull request.

## How It Works

Package mappings are stored in a structured JSON file that can be:
- Fetched from GitHub (updated automatically)
- Cached locally (24-hour TTL)
- Bundled with the package (offline fallback)

## File Structure

The mappings are stored in `src/pipwatch/mappings.json`:

```json
{
  "version": "1.0.0",
  "last_updated": "2024-02-11",
  "description": "Import name to PyPI package name mappings for Pipwatch",
  "mappings": {
    "import_name": {
      "package": "pypi-package-name",
      "category": "category-name",
      "verified": true
    }
  }
}
```

## Adding a New Mapping

### Step 1: Identify the Mapping

Find an import that doesn't map correctly:

```python
import cv2  # This should install opencv-python
```

### Step 2: Edit mappings.json

Add your mapping to `src/pipwatch/mappings.json`:

```json
{
  "mappings": {
    "cv2": {
      "package": "opencv-python",
      "category": "image-processing",
      "verified": true
    }
  }
}
```

### Step 3: Test Your Mapping

Test locally:

```bash
# Install in dev mode
pip install -e .

# Clear cache to test fresh
pipwatch --clear-cache

# Test your mapping
pipwatch test_file.py --dry-run
```

### Step 4: Add a Test

Add a test in `tests/test_mapping_registry.py`:

```python
def test_your_new_mapping():
    """Test the new mapping you added."""
    registry = MappingRegistry(use_cache=False)
    assert registry.get_package_name("cv2") == "opencv-python"
```

### Step 5: Submit Pull Request

1. Create a branch: `git checkout -b add-mapping-cv2`
2. Commit your changes: `git commit -m "Add mapping for cv2 -> opencv-python"`
3. Push: `git push origin add-mapping-cv2`
4. Open a Pull Request on GitHub

## Categories

Use consistent categories:

| Category | Description | Examples |
|----------|-------------|----------|
| `image-processing` | Image manipulation | PIL, cv2, skimage |
| `data-science` | Data analysis/ML | sklearn, pandas, numpy |
| `web-framework` | Web frameworks | flask, django, fastapi |
| `web-scraping` | Web scraping | bs4, lxml, scrapy |
| `database` | Database drivers | psycopg2, pymongo, mysqlclient |
| `http` | HTTP clients | requests, aiohttp, httpx |
| `cli` | CLI utilities | click, rich, tqdm |
| `cryptography` | Security/crypto | jwt, nacl, Crypto |

## How Users Get Your Mapping

Once your PR is merged:

1. **Immediate**: Users who run `pipwatch --update-mappings` get it right away
2. **Automatic**: Users get it within 24 hours (cache expiry)
3. **Bundled**: Next package release includes it in bundled mappings
