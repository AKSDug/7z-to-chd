"""Test utility functions."""

import pytest
import sys
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.utils import Timer, confirm_path


class TestTimer:
    """Test Timer functionality."""

    def test_timer_initialization(self):
        """Test timer can be initialized."""
        timer = Timer()
        assert timer.start_time is None
        assert timer.stop_time is None

    def test_timer_start(self):
        """Test timer can be started."""
        timer = Timer()
        timer.start()
        assert timer.start_time is not None
        assert timer.stop_time is None

    def test_timer_stop(self):
        """Test timer can be stopped."""
        timer = Timer()
        timer.start()
        timer.stop()
        assert timer.start_time is not None
        assert timer.stop_time is not None

    def test_timer_elapsed(self):
        """Test timer elapsed calculation."""
        timer = Timer()
        timer.start()
        timer.stop()
        elapsed = timer.elapsed()
        assert elapsed >= 0
        assert isinstance(elapsed, float)


class TestConfirmPath:
    """Test path confirmation functionality."""

    def test_confirm_existing_directory(self):
        """Test confirming an existing directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = confirm_path(temp_dir)
            assert result == Path(temp_dir)

    def test_confirm_nonexistent_directory_with_create(self):
        """Test confirming non-existent directory with create=True."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "new_directory"
            result = confirm_path(str(new_dir), create=True)
            assert result == new_dir
            assert new_dir.exists()

    def test_confirm_nonexistent_directory_without_create(self):
        """Test confirming non-existent directory without create."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "new_directory"
            with pytest.raises(FileNotFoundError):
                confirm_path(str(new_dir), create=False)

    def test_confirm_file_as_directory(self):
        """Test confirming a file when directory expected."""
        with tempfile.NamedTemporaryFile() as temp_file:
            with pytest.raises(NotADirectoryError):
                confirm_path(temp_file.name)
