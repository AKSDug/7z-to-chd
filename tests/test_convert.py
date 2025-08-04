"""Test convert.py functionality."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from convert import prompt_user_input


class TestPromptUserInput:
    """Test user input prompting functionality."""

    @patch("convert.input")
    @patch("convert.confirm_path")
    def test_default_keep_files_behavior(self, mock_confirm_path, mock_input):
        """Test that empty input defaults to keeping files (non-destructive)."""
        # Mock the arguments
        args = MagicMock()
        args.source = "/test/source"
        args.destination = "/test/dest"
        args.keep = None  # No command line arg provided
        args.threads = 4
        
        # Mock confirm_path to return Path objects
        mock_confirm_path.side_effect = lambda x, create=False: Path(x)
        
        # Mock input to return empty string (user just hits Enter)
        mock_input.return_value = ""
        
        # Call the function
        result = prompt_user_input(args)
        
        # Extract keep_files from result
        source_dir, dest_dir, keep_files, max_workers, state_file, skip_playlist_scan = result
        
        # Assert that default behavior keeps files (non-destructive)
        assert keep_files is True, "Default behavior should keep files (non-destructive)"

    @patch("convert.input")
    @patch("convert.confirm_path")
    def test_explicit_no_deletes_files(self, mock_confirm_path, mock_input):
        """Test that explicit 'no' input deletes files."""
        # Mock the arguments
        args = MagicMock()
        args.source = "/test/source"
        args.destination = "/test/dest"
        args.keep = None
        args.threads = 4
        
        # Mock confirm_path to return Path objects
        mock_confirm_path.side_effect = lambda x, create=False: Path(x)
        
        # Mock input to return "no"
        mock_input.return_value = "no"
        
        # Call the function
        result = prompt_user_input(args)
        
        # Extract keep_files from result
        source_dir, dest_dir, keep_files, max_workers, state_file, skip_playlist_scan = result
        
        # Assert that explicit "no" deletes files
        assert keep_files is False, "Explicit 'no' should delete files"

    @patch("convert.input")
    @patch("convert.confirm_path")
    def test_explicit_yes_keeps_files(self, mock_confirm_path, mock_input):
        """Test that explicit 'yes' input keeps files."""
        # Mock the arguments
        args = MagicMock()
        args.source = "/test/source"
        args.destination = "/test/dest"
        args.keep = None
        args.threads = 4
        
        # Mock confirm_path to return Path objects
        mock_confirm_path.side_effect = lambda x, create=False: Path(x)
        
        # Mock input to return "yes"
        mock_input.return_value = "yes"
        
        # Call the function
        result = prompt_user_input(args)
        
        # Extract keep_files from result
        source_dir, dest_dir, keep_files, max_workers, state_file, skip_playlist_scan = result
        
        # Assert that explicit "yes" keeps files
        assert keep_files is True, "Explicit 'yes' should keep files"

    def test_command_line_arg_yes(self):
        """Test command line argument --keep yes."""
        # Mock the arguments
        args = MagicMock()
        args.source = "/test/source"
        args.destination = "/test/dest"
        args.keep = "yes"
        args.threads = 4
        
        with patch("convert.confirm_path") as mock_confirm_path:
            mock_confirm_path.side_effect = lambda x, create=False: Path(x)
            
            result = prompt_user_input(args)
            source_dir, dest_dir, keep_files, max_workers, state_file, skip_playlist_scan = result
            
            assert keep_files is True, "Command line --keep yes should keep files"

    def test_command_line_arg_no(self):
        """Test command line argument --keep no."""
        # Mock the arguments
        args = MagicMock()
        args.source = "/test/source"
        args.destination = "/test/dest"
        args.keep = "no"
        args.threads = 4
        
        with patch("convert.confirm_path") as mock_confirm_path:
            mock_confirm_path.side_effect = lambda x, create=False: Path(x)
            
            result = prompt_user_input(args)
            source_dir, dest_dir, keep_files, max_workers, state_file, skip_playlist_scan = result
            
            assert keep_files is False, "Command line --keep no should delete files"