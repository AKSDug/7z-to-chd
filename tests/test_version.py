"""Test version management."""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from __version__ import __version__, __author__, __email__, __description__


def test_version_exists():
    """Test that version information exists."""
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_version_format():
    """Test that version follows semantic versioning."""
    parts = __version__.split(".")
    assert len(parts) >= 2, "Version should have at least major.minor format"

    # Check that major and minor are integers
    assert parts[0].isdigit(), "Major version should be a number"
    assert parts[1].isdigit(), "Minor version should be a number"


def test_author_info():
    """Test that author information is present."""
    assert __author__ == "AKSDug"
    assert "@" in __email__
    assert len(__description__) > 10


def test_current_version():
    """Test current version is 1.0.3."""
    assert __version__ == "1.0.3"
