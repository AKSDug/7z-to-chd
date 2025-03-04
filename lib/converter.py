#!/usr/bin/env python3
"""
7z-to-CHD Converter - Enhanced Converter Module
Handles the conversion of disc image files to CHD format with resource management
and resume functionality

Author: AKSDug
Repository: https://github.com/AKSDug/7z-to-chd
"""

import os
import logging
import shutil
import subprocess
import tempfile
import time
import psutil
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import colorama

# Set up logging
logger = logging.getLogger('converter')

class Converter:
    """Class for handling conversion of disc image files to CHD format with resource management and resume functionality."""
    
    def __init__(self, chdman_path=None, temp_dir=None, max_workers=None, extractor=None):
        """
        Initialize the converter.
        
        Args:
            chdman_path (str, optional): Path to chdman executable. Will search if not provided.
            temp_dir (str, optional): Directory for temporary files. Defaults to system temp directory.
            max_workers (int, optional): Maximum number of conversion workers. Defaults to CPU count.
            extractor (Extractor, optional): Reference to the Extractor object for tracking game series.
        """
        self.chdman_path = self._find_chdman(chdman_path)
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir()) / "7z-to-chd"
        self.max_workers = max_workers
        self.extractor = extractor
        self.playlist_generator = None  # Will be set later
        
        # Create temp directory if it doesn't exist
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Flag to indicate if we need to prompt for chdman path
        self.prompt_for_chdman = self.chdman_path is None
        
    def set_extractor(self, extractor):
        """
        Set reference to the Extractor object.
        
        Args:
            extractor: The Extractor object.
        """
        self.extractor = extractor
        
    def set_playlist_generator(self, playlist_generator):
        """
        Set reference to the PlaylistGenerator object.
        
        Args:
            playlist_generator: The PlaylistGenerator object.
        """
        self.playlist_generator = playlist_generator
    
    def _find_chdman(self, chdman_path=None):
        """
        Find the chdman executable.
        
        Args:
            chdman_path (str, optional): Path to chdman executable.
            
        Returns:
            Path: Path to chdman executable, or None if not found.
        """
        if chdman_path:
            chdman_path = Path(chdman_path)
            if chdman_path.exists():
                logger.info(f"Using specified chdman path: {chdman_path}")
                return chdman_path
            logger.warning(f"Specified chdman path {chdman_path} does not exist")
        
        # Check for stored chdman path in configuration file
        script_dir = Path(__file__).parents[1]
        config_file = script_dir / "chdman_path.txt"
        if config_file.exists():
            with open(config_file, 'r') as f:
                stored_path_str = f.read().strip()
                stored_path = Path(stored_path_str)
                if stored_path.exists():
                    logger.info(f"Using chdman from configuration file: {stored_path}")
                    return stored_path
                else:
                    logger.warning(f"Configured chdman path no longer exists: {stored_path}")
        
        # Check if chdman is in PATH
        chdman_in_path = shutil.which("chdman")
        if chdman_in_path:
            logger.info(f"Using chdman from PATH: {chdman_in_path}")
            # Save this path for future use
            try:
                with open(config_file, 'w') as f:
                    f.write(chdman_in_path)
            except Exception as e:
                logger.warning(f"Could not save chdman path to config file: {e}")
            return Path(chdman_in_path)
        
        logger.warning("chdman not found automatically")
        return None
    
    def _prompt_user_for_chdman(self):
        """
        Prompt the user to provide the path to chdman.
        
        Returns:
            Path: Path to chdman executable, or None if not provided.
        """
        print(f"\n{colorama.Fore.YELLOW}" + "="*60 + f"{colorama.Style.RESET_ALL}")
        print(f"{colorama.Fore.RED}chdman executable not found!{colorama.Style.RESET_ALL}")
        print("chdman is required for CHD conversion and is typically included with MAME.")
        print(f"{colorama.Fore.CYAN}Please enter the full path to the chdman executable:{colorama.Style.RESET_ALL}")
        print("Example: C:\\path\\to\\mame\\chdman.exe or /path/to/mame/chdman")
        print(f"{colorama.Fore.YELLOW}" + "="*60 + f"{colorama.Style.RESET_ALL}")
        
        user_path = input("> ").strip()
        
        if not user_path:
            logger.warning("No path provided")
            return None
        
        chdman_path = Path(user_path)
        
        # Check if the path is a directory, and if so, append chdman or chdman.exe
        if chdman_path.is_dir():
            # Try both chdman and chdman.exe
            for name in ["chdman", "chdman.exe"]:
                test_path = chdman_path / name
                if test_path.exists():
                    chdman_path = test_path
                    break
            else:
                logger.warning(f"No chdman executable found in directory: {chdman_path}")
                return None
        
        # Verify the path
        if chdman_path.exists():
            if chdman_path.is_file():
                # Try to make the file executable on Unix systems
                import platform
                if platform.system() != 'Windows' and not os.access(chdman_path, os.X_OK):
                    try:
                        os.chmod(chdman_path, 0o755)
                    except Exception as e:
                        logger.warning(f"Could not make chdman executable: {e}")
                
                # Store the path for future use
                try:
                    script_dir = Path(__file__).parents[1]
                    config_file = script_dir / "chdman_path.txt"
                    with open(config_file, 'w') as f:
                        f.write(str(chdman_path))
                    logger.info(f"chdman path stored in configuration file: {config_file}")
                except Exception as e:
                    logger.warning(f"Could not save chdman path: {e}")
                
                logger.info(f"Using user-provided chdman: {chdman_path}")
                return chdman_path
            else:
                logger.warning(f"Path exists but is not a file: {chdman_path}")
        else:
            logger.warning(f"Path does not exist: {chdman_path}")
        
        return None
    
    def _ensure_chdman_available(self):
        """
        Ensure chdman is available, prompting the user if necessary.
        
        Returns:
            bool: True if chdman is available, False otherwise.
        """
        if self.chdman_path is not None:
            # Verify the path still exists and is executable
            if not os.path.exists(self.chdman_path):
                logger.warning(f"Previously configured chdman path no longer exists: {self.chdman_path}")
                self.chdman_path = None
                self.prompt_for_chdman = True
            else:
                return True
        
        if self.prompt_for_chdman:
            print(f"\n{colorama.Fore.YELLOW}chdman not found automatically. You will be prompted to provide its location.{colorama.Style.RESET_ALL}")
            print(f"Common locations include:")
            print(f" - Windows: C:\\Program Files\\MAME\\chdman.exe")
            print(f" - macOS: /Applications/MAME.app/Contents/MacOS/chdman")
            print(f" - Linux: /usr/bin/chdman or /usr/local/bin/chdman")
            
            self.chdman_path = self._prompt_user_for_chdman()
            self.prompt_for_chdman = False  # Only prompt once per session
            
            if self.chdman_path is not None:
                # Save this path for future use
                try:
                    script_dir = Path(__file__).parents[1]
                    config_file = script_dir / "chdman_path.txt"
                    with open(config_file, 'w') as f:
                        f.write(str(self.chdman_path))
                    logger.info(f"Saved chdman path to config file: {config_file}")
                except Exception as e:
                    logger.warning(f"Could not save chdman path to config file: {e}")
                return True
            
            print(f"\n{colorama.Fore.RED}Error: chdman is required for conversion but was not provided.{colorama.Style.RESET_ALL}")
            logger.error("chdman is required for conversion but was not found or provided")
            return False
        
        return False
    
    def check_system_resources(self):
        """
        Check available system resources.
        
        Returns:
            dict: Available system resources including memory and CPU usage.
        """
        resources = {
            'memory_available': psutil.virtual_memory().available,
            'memory_percent': psutil.virtual_memory().percent,
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'disk_space': shutil.disk_usage(self.temp_dir).free
        }
        
        logger.debug(f"System resources: {resources['memory_percent']}% memory used, "
                   f"{resources['cpu_percent']}% CPU used, "
                   f"{resources['memory_available'] / (1024*1024*1024):.1f} GB memory available")
        
        return resources
    
    def estimate_file_complexity(self, input_file, input_type):
        """
        Estimate the complexity of a file for conversion.
        
        Args:
            input_file (Path): Input file path.
            input_type (str): Type of input file (iso, cue, gdi, etc.)
            
        Returns:
            str: Complexity category ('low', 'medium', 'high')
        """
        file_size = input_file.stat().st_size
        
        # CUE files may reference multiple tracks - check their complexity
        if input_type == 'cue':
            try:
                # Read the cue file to get referenced file sizes
                total_size = 0
                with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
                    cue_content = f.read()
                
                # Extract FILE references from CUE
                file_references = re.findall(r'FILE\s+"([^"]+)"', cue_content)
                if not file_references:
                    file_references = re.findall(r'FILE\s+([^\s"]+)', cue_content)
                
                # Sum up the sizes of all referenced files
                for ref in file_references:
                    ref_path = input_file.parent / ref
                    if ref_path.exists():
                        total_size += ref_path.stat().st_size
                
                # If we found referenced files, use their total size
                if total_size > 0:
                    file_size = total_size
            except Exception as e:
                logger.warning(f"Error analyzing cue file {input_file}: {e}")
        
        # Categorize by size
        if file_size > 2 * 1024 * 1024 * 1024:  # > 2GB
            return 'high'
        elif file_size > 650 * 1024 * 1024:  # > 650MB (typical CD size)
            return 'medium'
        else:
            return 'low'
    
    def calculate_optimal_workers(self, file_info_list):
        """
        Calculate the optimal number of worker threads based on file complexities and system resources.
        
        Args:
            file_info_list (list): List of tuples (input_file, input_type).
            
        Returns:
            dict: Mapping of complexity levels to worker counts.
        """
        # Analyze files by complexity
        files_by_complexity = {'low': 0, 'medium': 0, 'high': 0}
        
        for input_file, input_type in file_info_list:
            complexity = self.estimate_file_complexity(Path(input_file), input_type)
            files_by_complexity[complexity] += 1
        
        # Get system resources
        resources = self.check_system_resources()
        
        # Base calculation on available memory
        available_memory_gb = resources['memory_available'] / (1024 * 1024 * 1024)
        
        # Start with user-specified max_workers, or default to CPU count
        base_workers = self.max_workers
        
        # Calculate memory-based worker limits
        memory_based_low = max(1, int(available_memory_gb / 1))     # 1GB per low-complexity worker
        memory_based_medium = max(1, int(available_memory_gb / 2))  # 2GB per medium-complexity worker
        memory_based_high = max(1, int(available_memory_gb / 4))    # 4GB per high-complexity worker
        
        # Apply workers based on memory availability
        if resources['memory_percent'] > 80:
            # High memory pressure, reduce workers
            adjustment_factor = 0.5
        elif resources['memory_percent'] > 60:
            # Moderate memory pressure
            adjustment_factor = 0.7
        else:
            # Low memory pressure
            adjustment_factor = 1.0
        
        # Calculate and adjust workers
        workers = {
            'low': min(base_workers, max(1, int(memory_based_low * adjustment_factor))),
            'medium': min(base_workers // 2, max(1, int(memory_based_medium * adjustment_factor))),
            'high': min(2, max(1, int(memory_based_high * adjustment_factor)))
        }
        
        logger.info(f"Optimal workers: low={workers['low']}, "
                  f"medium={workers['medium']}, high={workers['high']}")
        
        return workers, files_by_complexity
    
    def extract_game_info(self, filename):
        """
        Extract the base game name and disc number from a filename.
        
        Args:
            filename (str): Filename to parse.
            
        Returns:
            tuple: (base_name, disc_number) or (filename, None) if no disc pattern found.
        """
        # Common disc identifier patterns
        disc_patterns = [
            r'(?i)[\[(]?disc\s*(\d+)[\])]?',            # (Disc 1), [Disc 2], Disc 3
            r'(?i)[\[(]?cd\s*(\d+)[\])]?',              # (CD 1), [CD 2], CD 3
            r'(?i)[\[(]?disk\s*(\d+)[\])]?',            # (Disk 1), [Disk 2], Disk 3
            r'(?i)[\[(]?volume\s*(\d+)[\])]?',          # (Volume 1), [Volume 2]
            r'(?i)[\[(]?vol\s*(\d+)[\])]?',             # (Vol 1), [Vol 2]
            r'(?i)[\[(]?d(\d+)[\])]?',                  # (D1), [D2], D3
            r'(?i)[\s\-\_\.]+d(\d+)[\s\-\_\.]?',        # Game - D1, Game_D2, Game.D3
            r'[\s\-\_\.]+(\d+)[\s\-\_\.]?'              # Game - 1, Game_2, Game.3
        ]
        
        # Strip extension
        name = Path(filename).stem
        
        # Try to match disc patterns
        for pattern in disc_patterns:
            match = re.search(pattern, name)
            if match:
                disc_num = int(match.group(1))
                # Remove the disc information from the name
                base_name = re.sub(pattern, '', name).strip(' -_.')
                return base_name, disc_num
        
        # No disc pattern found
        return name, None

    def convert_file(self, input_file, output_file, input_type):
        """
        Convert a file to CHD with resume functionality.
        
        Args:
            input_file (str): Input file path.
            output_file (str): Output CHD file path.
            input_type (str): Type of input file (iso, cue, gdi, etc.)
            
        Returns:
            bool: True if conversion was successful, False otherwise.
        """
        input_file = Path(input_file)
        output_file = Path(output_file)
        
        # Check if output file already exists (resume functionality)
        if output_file.exists():
            logger.info(f"Output file already exists, skipping conversion: {output_file}")
            
            # Track for M3U creation if this is part of a multi-disc game
            base_game, disc_num = self.extract_game_info(input_file.stem)
            if base_game and disc_num and self.extractor:
                # Update the extractor's tracking information
                if base_game not in self.extractor.processed_games:
                    self.extractor.processed_games[base_game] = []
                if disc_num not in self.extractor.processed_games[base_game]:
                    self.extractor.processed_games[base_game].append(disc_num)
                    
                # Check if this was the final disc in a series and create M3U
                if self.playlist_generator and len(self.extractor.processed_games[base_game]) >= 2:
                    # Trigger immediate M3U creation for this game series
                    if base_game not in self.extractor.get_completed_series():
                        self._create_m3u_for_game(base_game, output_file.parent)
                        self.extractor.mark_game_series_complete(base_game)
            
            return True
        
        if not input_file.exists():
            logger.error(f"Input file does not exist: {input_file}")
            return False
        
        # We should prioritize .cue files for multi-track games
        if input_type == 'bin' and any(pattern in input_file.stem for pattern in ['(Track 1)', '(Track 2)', '(Track 3)', '(Track 4)', '(Track 5)']):
            logger.debug(f"Skipping individual track file: {input_file}")
            return False
        
        # Check file complexity
        complexity = self.estimate_file_complexity(input_file, input_type)
        
        # Check system resources before conversion
        resources = self.check_system_resources()
        
        # If memory is critically low (>90% used), wait for resources to free up
        retry_count = 0
        while resources['memory_percent'] > 90 and retry_count < 3:
            logger.warning(f"Memory usage is high ({resources['memory_percent']}%), "
                         f"waiting before conversion: {input_file.name}")
            time.sleep(10)  # Wait 10 seconds
            resources = self.check_system_resources()
            retry_count += 1
        
        # Ensure chdman is available
        if not self._ensure_chdman_available():
            return False
        
        logger.info(f"Converting {input_file} to {output_file} (complexity: {complexity})")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_file.parent, exist_ok=True)
        
        # Map input_type to chdman command
        command = "createcd"  # Default for most disc types
        
        # Build the command
        cmd = [
            str(self.chdman_path),
            command,
            "-i", str(input_file),
            "-o", str(output_file)
        ]
        
        try:
            # Run chdman
            logger.debug(f"Running command: {' '.join(cmd)}")
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            # Check if the conversion was successful
            success = process.returncode == 0 and output_file.exists()
            
            if success:
                logger.info(f"Conversion successful: {output_file}")
                
                # Track for M3U creation if this is part of a multi-disc game
                base_game, disc_num = self.extract_game_info(input_file.stem)
                if base_game and disc_num and self.extractor:
                    # Update the extractor's tracking information
                    if base_game not in self.extractor.processed_games:
                        self.extractor.processed_games[base_game] = []
                    if disc_num not in self.extractor.processed_games[base_game]:
                        self.extractor.processed_games[base_game].append(disc_num)
                        
                    # Check if this was the final disc in a series and create M3U
                    if self.playlist_generator and len(self.extractor.processed_games[base_game]) >= 2:
                        # Trigger immediate M3U creation for this game series
                        if base_game not in self.extractor.get_completed_series():
                            self._create_m3u_for_game(base_game, output_file.parent)
                            self.extractor.mark_game_series_complete(base_game)
                
                return True
            else:
                logger.error(f"Conversion failed with return code {process.returncode}")
                logger.error(f"STDOUT: {process.stdout}")
                logger.error(f"STDERR: {process.stderr}")
                return False
        
        except Exception as e:
            logger.error(f"Error during conversion: {e}")
            return False
    
    def _create_m3u_for_game(self, base_game, output_dir):
        """
        Create an M3U playlist for a multi-disc game.
        
        Args:
            base_game (str): Base name of the game.
            output_dir (Path): Directory where CHD files are stored.
            
        Returns:
            bool: True if M3U created successfully, False otherwise.
        """
        if not self.playlist_generator:
            logger.warning("Playlist generator not set, cannot create M3U")
            return False
            
        if not self.extractor:
            logger.warning("Extractor not set, cannot access game information")
            return False
        
        # Get disc numbers for this game series
        processed_games = self.extractor.get_processed_games()
        if base_game not in processed_games or len(processed_games[base_game]) <= 1:
            # Not a multi-disc game or not enough discs processed
            return False
        
        # Check if M3U already exists
        m3u_path = output_dir / f"{base_game}.m3u"
        if m3u_path.exists():
            logger.info(f"M3U already exists: {m3u_path}")
            return True
        
        # Build the list of CHD files for this game series
        disc_files = []
        for disc_num in sorted(processed_games[base_game]):
            # For each disc number, find the corresponding CHD file
            for chd_file in output_dir.glob("*.chd"):
                file_base_game, file_disc_num = self.extract_game_info(chd_file.stem)
                if file_base_game == base_game and file_disc_num == disc_num:
                    disc_files.append((chd_file, disc_num))
                    break
        
        if not disc_files:
            logger.warning(f"No CHD files found for game series: {base_game}")
            return False
        
        # Create the M3U playlist
        try:
            logger.info(f"Creating M3U playlist for {base_game} with {len(disc_files)} discs")
            
            # Create the actual M3U playlist file
            with open(m3u_path, 'w', encoding='utf-8') as f:
                # Write header comment
                f.write(f"# {base_game} - Multi-disc game playlist\n")
                f.write("# Created by 7z-to-CHD Converter\n")
                f.write("#\n")
                
                # Write disc entries sorted by disc number
                for file_path, disc_num in sorted(disc_files, key=lambda x: x[1]):
                    # Just write the filename to make it portable
                    f.write(f"{file_path.name}\n")
            
            logger.info(f"M3U playlist created successfully: {m3u_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create M3U playlist: {e}")
            return False

    def convert_multiple(self, file_info_list, output_dir):
        """
        Convert multiple files to CHD with adaptive worker allocation and resume functionality.
        
        Args:
            file_info_list (list): List of tuples (input_file, input_type).
            output_dir (str): Directory to store CHD files.
            
        Returns:
            dict: Mapping of input files to (output_file, success) tuples.
        """
        # Ensure chdman is available before starting batch processing
        if not self._ensure_chdman_available():
            print(f"\n{colorama.Fore.RED}Error: chdman executable is required but was not found or provided.{colorama.Style.RESET_ALL}")
            print("Conversion cannot proceed without chdman. Aborting the conversion process.")
            return {}
        
        output_dir = Path(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        
        # Set output directory for extractor if available (for resume functionality)
        if self.extractor:
            self.extractor.set_output_directory(output_dir)
        
        # If no files to convert, return empty result
        if not file_info_list:
            return {}
        
        # Check for existing CHD files (resume functionality)
        resumable_file_info = []
        skipped_files = 0
        
        for input_file, input_type in file_info_list:
            # Check if output file already exists
            output_file = output_dir / f"{Path(input_file).stem}.chd"
            if output_file.exists():
                logger.debug(f"Skipping already converted file: {output_file}")
                skipped_files += 1
                
                # Track for M3U creation if part of a multi-disc game
                base_game, disc_num = self.extract_game_info(Path(input_file).stem)
                if base_game and disc_num and self.extractor:
                    if base_game not in self.extractor.processed_games:
                        self.extractor.processed_games[base_game] = []
                    if disc_num not in self.extractor.processed_games[base_game]:
                        self.extractor.processed_games[base_game].append(disc_num)
                        
                    # Check if this completes a multi-disc series
                    if len(self.extractor.processed_games[base_game]) >= 2:
                        # Trigger immediate M3U creation
                        if base_game not in self.extractor.get_completed_series():
                            self._create_m3u_for_game(base_game, output_dir)
                            self.extractor.mark_game_series_complete(base_game)
            else:
                resumable_file_info.append((input_file, input_type))
        
        if skipped_files > 0:
            logger.info(f"Skipping {skipped_files} already converted files")
        
        # If all files are already converted, return early
        if not resumable_file_info:
            logger.info("All files already converted, nothing to do")
            
            # Process any multi-disc games that need M3U files
            if self.extractor:
                self.extractor.process_archive_series()
            
            # Create any missing M3U files for known multi-disc games
            if self.extractor and self.playlist_generator:
                processed_games = self.extractor.get_processed_games()
                for base_game, disc_nums in processed_games.items():
                    if len(disc_nums) > 1 and base_game not in self.extractor.get_completed_series():
                        self._create_m3u_for_game(base_game, output_dir)
                        self.extractor.mark_game_series_complete(base_game)
            
            return {}
        
        # Calculate optimal workers and group files by complexity
        optimal_workers, files_by_complexity = self.calculate_optimal_workers(resumable_file_info)
        
        logger.info(f"Converting {len(resumable_file_info)} files: "
                  f"{files_by_complexity['low']} low, "
                  f"{files_by_complexity['medium']} medium, "
                  f"{files_by_complexity['high']} high complexity")
        
        # Group files by complexity
        low_complexity = []
        medium_complexity = []
        high_complexity = []
        
        for input_file, input_type in resumable_file_info:
            complexity = self.estimate_file_complexity(Path(input_file), input_type)
            if complexity == 'low':
                low_complexity.append((input_file, input_type))
            elif complexity == 'medium':
                medium_complexity.append((input_file, input_type))
            else:
                high_complexity.append((input_file, input_type))
        
        results = {}
        
        # Process high complexity files first (potentially freeing up references to large files)
        if high_complexity:
            logger.info(f"Converting {len(high_complexity)} high complexity files")
            high_results = self._convert_batch(
                high_complexity, 
                output_dir,
                optimal_workers['high']
            )
            results.update(high_results)
            
            # Check for completed series after each batch
            if self.extractor:
                self.extractor.process_archive_series()
        
        # Process medium complexity files
        if medium_complexity:
            logger.info(f"Converting {len(medium_complexity)} medium complexity files")
            medium_results = self._convert_batch(
                medium_complexity, 
                output_dir,
                optimal_workers['medium']
            )
            results.update(medium_results)
            
            # Check for completed series after each batch
            if self.extractor:
                self.extractor.process_archive_series()
        
        # Process low complexity files
        if low_complexity:
            logger.info(f"Converting {len(low_complexity)} low complexity files")
            low_results = self._convert_batch(
                low_complexity, 
                output_dir,
                optimal_workers['low']
            )
            results.update(low_results)
            
            # Check for completed series after each batch
            if self.extractor:
                self.extractor.process_archive_series()
        
        # Count successful conversions
        successful = sum(1 for _, (_, success) in results.items() if success)
        logger.info(f"Conversion complete: {successful}/{len(resumable_file_info)} successful, "
                  f"{skipped_files} already converted")
        
        # Create any missing M3U files for multi-disc games
        if self.extractor and self.playlist_generator:
            processed_games = self.extractor.get_processed_games()
            for base_game, disc_nums in processed_games.items():
                if len(disc_nums) > 1 and base_game not in self.extractor.get_completed_series():
                    self._create_m3u_for_game(base_game, output_dir)
                    self.extractor.mark_game_series_complete(base_game)
            
            # Also check for incomplete series that might not have all discs
            # but would still benefit from an M3U playlist
            self.playlist_generator.check_for_incomplete_series()
        
        return results
    
    def _convert_batch(self, file_info_list, output_dir, workers):
        """
        Convert a batch of files with a specified number of workers.
        Checks after each file completion if any series are now complete for M3U creation.
        
        Args:
            file_info_list (list): List of tuples (input_file, input_type).
            output_dir (Path): Directory to store CHD files.
            workers (int): Number of worker threads.
            
        Returns:
            dict: Mapping of input files to (output_file, success) tuples.
        """
        results = {}
        
        # Limit workers to the number of files
        effective_workers = min(workers, len(file_info_list))
        logger.info(f"Converting {len(file_info_list)} files using {effective_workers} workers")
        
        # Single worker - process sequentially for more predictable M3U timing
        if effective_workers == 1 or len(file_info_list) == 1:
            for input_file, input_type in file_info_list:
                input_file = Path(input_file)
                # Create output filename with the same name but .chd extension
                output_file = output_dir / f"{input_file.stem}.chd"
                
                success = self.convert_file(input_file, output_file, input_type)
                results[input_file] = (output_file, success)
                
                # Check for completed series after each file
                if self.extractor:
                    self.extractor.process_archive_series()
                
                # Brief pause between completions to allow resource reclamation
                time.sleep(0.5)
            
            return results
        
        # Multiple workers
        with ThreadPoolExecutor(max_workers=effective_workers) as executor:
            # Submit conversion tasks
            future_to_file = {}
            
            for input_file, input_type in file_info_list:
                input_file = Path(input_file)
                # Create output filename with the same name but .chd extension
                output_file = output_dir / f"{input_file.stem}.chd"
                
                future = executor.submit(
                    self.convert_file,
                    input_file,
                    output_file,
                    input_type
                )
                
                future_to_file[future] = (input_file, output_file)
            
            # Process results as they complete
            for future in future_to_file:
                input_file, output_file = future_to_file[future]
                try:
                    success = future.result()
                    results[input_file] = (output_file, success)
                    
                    # Check if any series are now complete after each file
                    if self.extractor:
                        self.extractor.process_archive_series()
                    
                    # Brief pause between completions to allow resource reclamation
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Conversion failed for {input_file}: {e}")
                    results[input_file] = (None, False)
        
        return results
    
    def cleanup(self):
        """Clean up temporary files."""
        logger.info(f"Cleaning up temporary files in {self.temp_dir}")
        
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            logger.info("Cleanup successful")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")