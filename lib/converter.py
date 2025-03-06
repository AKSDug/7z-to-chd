#!/usr/bin/env python3
"""
7z-to-CHD Converter - Enhanced Converter Module
Handles the conversion of disc image files to CHD format with improved
parallelism and resource management
Version 1.0.1

Author: AKSDug
Repository: https://github.com/AKSDug/7z-to-chd
"""

import os
import logging
import subprocess
import shutil
import re
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import tempfile

# Set up logging
logger = logging.getLogger('converter')

class Converter:
    """Class for handling conversion of disc image files to CHD format."""
    
    def __init__(self, max_workers=None, chdman_path=None):
        """
        Initialize the converter.
        
        Args:
            max_workers (int, optional): Maximum number of conversion workers. Defaults to CPU count.
            chdman_path (str, optional): Path to chdman executable. Defaults to None (auto-detect).
        """
        self.max_workers = max_workers
        self.chdman_path = self._find_chdman() if chdman_path is None else Path(chdman_path)
        
        # Initialize reference to extractor and playlist manager (will be set later)
        self.extractor = None
        self.playlist_manager = None
        
        logger.debug(f"Converter initialized with max_workers={max_workers}, chdman_path={self.chdman_path}")
    
    def set_extractor(self, extractor):
        """
        Set reference to the Extractor object.
        
        Args:
            extractor: The Extractor object.
        """
        self.extractor = extractor
        logger.debug("Extractor set for Converter")
    
    def set_playlist_manager(self, playlist_manager):
        """
        Set reference to the PlaylistManager object.
        
        Args:
            playlist_manager: The PlaylistManager object.
        """
        self.playlist_manager = playlist_manager
        logger.debug("PlaylistManager set for Converter")
    
    def _find_chdman(self):
        """
        Find the chdman executable.
        
        Returns:
            Path: Path to chdman executable.
            
        Raises:
            FileNotFoundError: If chdman is not found.
        """
        # Check if chdman_path.txt exists in the project root
        script_dir = Path(__file__).parent.parent
        config_file = script_dir / "chdman_path.txt"
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                chdman_path = f.read().strip()
            
            # Validate the path
            if os.path.exists(chdman_path):
                logger.info(f"Using chdman from config file: {chdman_path}")
                return Path(chdman_path)
        
        # Check if chdman is in PATH
        chdman_in_path = shutil.which('chdman')
        if chdman_in_path:
            logger.info(f"Using chdman from PATH: {chdman_in_path}")
            return Path(chdman_in_path)
        
        # Try common installation locations
        common_locations = []
        
        # Windows
        if os.name == 'nt':
            common_locations.extend([
                Path(r"C:\Program Files\MAME\chdman.exe"),
                Path(r"C:\Program Files (x86)\MAME\chdman.exe"),
                script_dir / "tools" / "chdman" / "chdman.exe"
            ])
        # macOS
        elif os.name == 'posix' and 'darwin' in os.uname().sysname.lower():
            common_locations.extend([
                Path("/Applications/MAME.app/Contents/MacOS/chdman"),
                Path.home() / "Applications" / "MAME.app" / "Contents" / "MacOS" / "chdman",
                script_dir / "tools" / "chdman" / "chdman"
            ])
        # Linux
        elif os.name == 'posix':
            common_locations.extend([
                Path("/usr/bin/chdman"),
                Path("/usr/local/bin/chdman"),
                script_dir / "tools" / "chdman" / "chdman"
            ])
        
        # Check each location
        for location in common_locations:
            if location.exists():
                logger.info(f"Using chdman from common location: {location}")
                return location
        
        # Not found, will need to prompt user
        raise FileNotFoundError("chdman executable not found. Please run setup.py or manually specify the path.")
    
    def convert_to_chd(self, input_file, output_dir=None, overwrite=False):
        """
        Convert a disc image file to CHD format.
        
        Args:
            input_file (str): Path to input file.
            output_dir (str, optional): Directory to save CHD file. Defaults to same directory as input.
            overwrite (bool, optional): Whether to overwrite existing files. Defaults to False.
            
        Returns:
            tuple: (output_file, success) where output_file is the path to the created CHD file
                  and success is a boolean indicating whether conversion was successful.
        """
        input_path = Path(input_file)
        
        # Determine output directory and filename
        output_directory = Path(output_dir) if output_dir else input_path.parent
        output_file = output_directory / f"{input_path.stem}.chd"
        
        # Create output directory if it doesn't exist
        os.makedirs(output_directory, exist_ok=True)
        
        # Skip if output file already exists and overwrite is False
        if output_file.exists() and not overwrite:
            logger.info(f"Skipping conversion of {input_path.name} - CHD already exists: {output_file.name}")
            
            # Register with PlaylistManager if available
            if self.playlist_manager:
                base_game, disc_num = self.playlist_manager._extract_base_name_and_disc(input_path.stem)
                if base_game and disc_num:
                    self.playlist_manager.register_disc(output_file)
            # Legacy tracking via Extractor
            elif self.extractor:
                base_game, disc_num = self.extractor._extract_game_info(input_path.stem)
                if base_game and disc_num:
                    if hasattr(self.extractor, 'processed_games'):
                        if base_game not in self.extractor.processed_games:
                            self.extractor.processed_games[base_game] = []
                        if disc_num not in self.extractor.processed_games[base_game]:
                            self.extractor.processed_games[base_game].append(disc_num)
            
            return output_file, True
        
        # Determine input file type and corresponding chdman command
        input_extension = input_path.suffix.lower()
        
        # Get base command based on file extension
        if input_extension == '.cue':
            command = [str(self.chdman_path), 'createcd', '-i', str(input_path), '-o', str(output_file)]
        elif input_extension == '.gdi':
            command = [str(self.chdman_path), 'createcd', '-i', str(input_path), '-o', str(output_file)]
        elif input_extension == '.toc':
            command = [str(self.chdman_path), 'createcd', '-i', str(input_path), '-o', str(output_file)]
        elif input_extension == '.nrg':
            command = [str(self.chdman_path), 'createcd', '-i', str(input_path), '-o', str(output_file)]
        elif input_extension == '.cdi':
            command = [str(self.chdman_path), 'createcd', '-i', str(input_path), '-o', str(output_file)]
        elif input_extension == '.iso' or input_extension == '.bin' or input_extension == '.img':
            command = [str(self.chdman_path), 'createcd', '-i', str(input_path), '-o', str(output_file)]
        else:
            logger.warning(f"Unsupported file type: {input_extension}")
            return None, False
        
        # Add common options
        command.extend(['-f'])  # Force overwrite
        
        logger.info(f"Converting {input_path.name} to CHD")
        logger.debug(f"Command: {' '.join(command)}")
        
        try:
            # Execute chdman
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            
            # Check for successful conversion
            if result.returncode == 0:
                logger.info(f"Successfully converted {input_path.name} to CHD: {output_file.name}")
                
                # Register with PlaylistManager if available
                if self.playlist_manager:
                    base_game, disc_num = self.playlist_manager._extract_base_name_and_disc(input_path.stem)
                    if base_game and disc_num:
                        self.playlist_manager.register_disc(output_file)
                # Legacy tracking via Extractor
                elif self.extractor:
                    base_game, disc_num = self.extractor._extract_game_info(input_path.stem)
                    if base_game and disc_num:
                        if hasattr(self.extractor, 'processed_games'):
                            if base_game not in self.extractor.processed_games:
                                self.extractor.processed_games[base_game] = []
                            if disc_num not in self.extractor.processed_games[base_game]:
                                self.extractor.processed_games[base_game].append(disc_num)
                
                return output_file, True
            else:
                logger.error(f"Failed to convert {input_path.name} to CHD. Error: {result.stderr}")
                return None, False
        
        except Exception as e:
            logger.error(f"Error during conversion of {input_path.name}: {e}")
            return None, False
    
    def convert_multiple(self, file_list, output_dir=None):
        """
        Convert multiple files to CHD format.
        
        Args:
            file_list (list): List of tuples (file_path, file_type) to convert.
            output_dir (str, optional): Directory to save CHD files. Defaults to same directory as input.
            
        Returns:
            dict: Mapping of input files to (output_file, success) tuples.
        """
        if not file_list:
            logger.warning("No files provided for conversion")
            return {}
        
        # Prepare output dictionary
        results = {}
        
        # Calculate effective workers based on list size
        effective_workers = min(self.max_workers, len(file_list))
        
        # Convert files with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=effective_workers) as executor:
            future_to_file = {}
            
            for file_path, _ in file_list:
                logger.debug(f"Submitting file for conversion: {file_path}")
                future = executor.submit(self.convert_to_chd, file_path, output_dir)
                future_to_file[future] = file_path
            
            # Process results as they complete
            for future in future_to_file:
                file_path = future_to_file[future]
                try:
                    output_file, success = future.result()
                    results[file_path] = (output_file, success)
                    
                    # After each conversion, check if any series are complete and need playlists
                    if self.extractor and hasattr(self.extractor, 'process_archive_series'):
                        self.extractor.process_archive_series()
                    
                except Exception as e:
                    logger.error(f"Conversion failed for {file_path}: {e}")
                    results[file_path] = (None, False)
        
        # Process any final playlists
        if self.playlist_manager:
            # Let PlaylistManager handle completion checking
            pass
        elif self.extractor and hasattr(self.extractor, 'process_archive_series'):
            self.extractor.process_archive_series()
        
        return results
    
    def check_conversion_tools(self):
        """
        Check if conversion tools are installed and working.
        
        Returns:
            bool: True if all tools are available, False otherwise.
        """
        # Check if chdman is available
        if not self.chdman_path or not self.chdman_path.exists():
            logger.error("chdman not found")
            return False
        
        # Try running chdman to check if it works
        try:
            result = subprocess.run([str(self.chdman_path), '--help'], 
                                   capture_output=True, text=True, check=False)
            
            if result.returncode != 0:
                logger.error(f"chdman test failed with error: {result.stderr}")
                return False
            
            logger.info("chdman test successful")
            return True
        
        except Exception as e:
            logger.error(f"Error testing chdman: {e}")
            return False
    
    def prompt_for_chdman(self):
        """
        Prompt the user to provide the path to chdman.
        
        Returns:
            Path: Path to chdman executable.
        """
        script_dir = Path(__file__).parent.parent
        config_file = script_dir / "chdman_path.txt"
        
        print("\n" + "="*60)
        print("chdman executable is required for CHD conversion.")
        print("Please enter the full path to the chdman executable:")
        print("Examples:")
        print("  Windows: C:\\Program Files\\MAME\\chdman.exe")
        print("  macOS: /Applications/MAME.app/Contents/MacOS/chdman")
        print("  Linux: /usr/bin/chdman or /usr/local/bin/chdman")
        print("="*60)
        
        while True:
            user_path = input("> ").strip()
            
            if not user_path:
                print("No path provided, please try again.")
                continue
            
            # Convert to Path object
            chdman_path = Path(user_path)
            
            # Verify the path
            if chdman_path.exists() and chdman_path.is_file():
                # Save the path to config file
                with open(config_file, 'w') as f:
                    f.write(str(chdman_path))
                
                print(f"chdman path saved: {chdman_path}")
                return chdman_path
            else:
                print(f"Invalid path: {user_path}")
                print("The file does not exist or is not a valid executable.")
                print("Please enter a valid path to chdman.")
    
    def cleanup(self):
        """Clean up temporary files."""
        logger.debug("Converter cleanup completed")


# Main function for testing
if __name__ == "__main__":
    # Set up logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    import sys
    
    # Create converter
    converter = Converter()
    
    # Check if chdman is available
    if not converter.check_conversion_tools():
        print("chdman not found or not working.")
        print("Please provide the path to chdman:")
        converter.chdman_path = converter.prompt_for_chdman()
    
    # Test conversion if file provided
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        print(f"Converting {input_file} to CHD")
        
        output_file, success = converter.convert_to_chd(input_file)
        
        if success:
            print(f"Conversion successful: {output_file}")
        else:
            print("Conversion failed")