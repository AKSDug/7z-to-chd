#!/usr/bin/env python3
"""
7z-to-CHD Converter - Enhanced Extractor Module
Handles the extraction of .7z archives with adaptive resource management
and resume functionality
Version 1.0.2

Author: AKSDug
Repository: https://github.com/AKSDug/7z-to-chd
"""

import os
import logging
import shutil
import tempfile
import time
import psutil
import re
from pathlib import Path
import py7zr
from concurrent.futures import ThreadPoolExecutor

# Set up logging
logger = logging.getLogger('extractor')

# Constants for archive size classifications
SIZE_THRESHOLD_LARGE = 4 * 1024 * 1024 * 1024  # 4GB
SIZE_THRESHOLD_MEDIUM = 1 * 1024 * 1024 * 1024  # 1GB
SIZE_THRESHOLD_SMALL = 100 * 1024 * 1024  # 100MB

class Extractor:
    """Class for handling extraction of .7z archives with adaptive resource management and resume capability."""
    
    def __init__(self, temp_dir=None, max_workers=None, output_dir=None):
        """
        Initialize the extractor.
        
        Args:
            temp_dir (str, optional): Directory for temporary files. Defaults to system temp directory.
            max_workers (int, optional): Maximum number of extraction workers. Defaults to CPU count.
            output_dir (str, optional): Output directory where CHD files will be stored. Used for resume functionality.
        """
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir()) / "7z-to-chd"
        self.max_workers = max_workers
        self.output_dir = Path(output_dir) if output_dir else None
        self.extraction_queue = []
        
        # Track processed games for M3U creation (legacy tracking, can be replaced by PlaylistManager)
        self.processed_games = {}
        self.completed_game_series = set()
        
        # Reference to the playlist manager (will be set later)
        self.playlist_manager = None
        
        # Create temp directory if it doesn't exist
        os.makedirs(self.temp_dir, exist_ok=True)
        
        logger.debug(f"Extractor initialized with temp_dir={self.temp_dir}, max_workers={max_workers}")
        
    def set_output_directory(self, output_dir):
        """
        Set the output directory for CHD files (needed for resume functionality).
        
        Args:
            output_dir (str): Path to output directory.
        """
        self.output_dir = Path(output_dir)
        logger.debug(f"Output directory set to {self.output_dir}")
        
    def set_playlist_manager(self, playlist_manager):
        """
        Set reference to the PlaylistManager object.
        
        Args:
            playlist_manager: The PlaylistManager object.
        """
        self.playlist_manager = playlist_manager
        logger.debug("PlaylistManager set for Extractor")
    
    def _extract_game_info(self, filename):
        """
        Extract the base game name and disc number from a filename.
        
        Args:
            filename (str): Filename to parse.
            
        Returns:
            tuple: (base_name, disc_number) or (filename, None) if no disc pattern found.
        """
        # If we have a PlaylistManager, use its extraction method for consistency
        if self.playlist_manager:
            return self.playlist_manager._extract_base_name_and_disc(filename)
            
        # Legacy implementation
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
    
    def analyze_archive(self, archive_path):
        """
        Analyze a .7z archive to estimate its size and complexity.
        Also checks if the contained files already exist in the output directory.
        
        Args:
            archive_path (str): Path to the .7z archive.
            
        Returns:
            dict: Analysis results including total size, file count, largest file size,
                  complexity category, and whether processing can be skipped.
        """
        archive_path = Path(archive_path)
        
        # Default analysis results
        analysis = {
            'path': archive_path,
            'size': 0,
            'compressed_size': archive_path.stat().st_size if archive_path.exists() else 0,
            'file_count': 0,
            'largest_file': 0,
            'complexity': 'unknown',
            'has_disc_images': False,
            'can_skip': False,
            'base_game': None,
            'disc_number': None,
            'convertible_files': []
        }
        
        logger.debug(f"Analyzing archive: {archive_path}")
        
        # Extract base game name and disc number from archive name
        base_game, disc_number = self._extract_game_info(archive_path.stem)
        analysis['base_game'] = base_game
        analysis['disc_number'] = disc_number
        
        # Pre-check if we can skip extraction based on output directory and archive name
        if self.output_dir and self.output_dir.exists():
            # For multi-disc games, check if the corresponding CHD exists
            if base_game and disc_number:
                chd_pattern = f"{archive_path.stem}.chd"
                chd_path = self.output_dir / chd_pattern
                
                if chd_path.exists():
                    logger.info(f"Archive {archive_path.name} can be skipped - CHD already exists: {chd_path.name}")
                    analysis['can_skip'] = True
                    
                    # Register with PlaylistManager if available
                    if self.playlist_manager:
                        # Register the disc but don't update playlists yet - we'll do that in batch after all processing
                        self.playlist_manager.register_disc(chd_path, update_playlists=False)
                    # Legacy tracking
                    else:
                        if base_game not in self.processed_games:
                            self.processed_games[base_game] = []
                        if disc_number not in self.processed_games[base_game]:
                            self.processed_games[base_game].append(disc_number)
                    
                    return analysis
            else:
                # For single-disc games, try matching archive name
                chd_pattern = f"{archive_path.stem}.chd"
                chd_path = self.output_dir / chd_pattern
                
                if chd_path.exists():
                    logger.info(f"Archive {archive_path.name} can be skipped - CHD already exists: {chd_path.name}")
                    analysis['can_skip'] = True
                    return analysis
        
        # If we can't pre-determine skip status, analyze the archive contents
        try:
            with py7zr.SevenZipFile(archive_path, mode='r') as z:
                # Get file information
                file_info_list = z.list()
                analysis['file_count'] = len(file_info_list)
                
                # Examine each file in the archive
                disc_extensions = ['.iso', '.bin', '.img', '.cue', '.gdi', '.toc', '.nrg', '.cdi']
                
                # Track potentially convertible files
                convertible_files = []
                
                for file_info in file_info_list:
                    # Update size metrics
                    uncompressed_size = file_info.uncompressed
                    analysis['size'] += uncompressed_size
                    analysis['largest_file'] = max(analysis['largest_file'], uncompressed_size)
                    
                    # Check if file is a disc image
                    filename = file_info.filename.lower()
                    if any(filename.endswith(ext) for ext in disc_extensions):
                        analysis['has_disc_images'] = True
                        convertible_files.append(file_info.filename)
                
                analysis['convertible_files'] = convertible_files
            
            # Determine complexity based on size
            if analysis['size'] >= SIZE_THRESHOLD_LARGE:
                analysis['complexity'] = 'high'
            elif analysis['size'] >= SIZE_THRESHOLD_MEDIUM:
                analysis['complexity'] = 'medium'
            elif analysis['size'] >= SIZE_THRESHOLD_SMALL:
                analysis['complexity'] = 'low'
            else:
                analysis['complexity'] = 'minimal'
            
            # Check if processing can be skipped (if all convertible files already exist as CHDs)
            if self.output_dir and analysis['has_disc_images'] and convertible_files:
                can_skip = True
                for filename in convertible_files:
                    # Get base name without extension
                    file_base = Path(filename).stem
                    chd_name = f"{file_base}.chd"
                    chd_path = self.output_dir / chd_name
                    if not chd_path.exists():
                        can_skip = False
                        break
                
                analysis['can_skip'] = can_skip
                
                if can_skip:
                    logger.info(f"Archive {archive_path.name} can be skipped - all CHDs already exist")
                    
                    # Register with PlaylistManager if available
                    if self.playlist_manager and base_game and disc_number:
                        # Locate the CHD file and register it without updating playlists yet
                        chd_pattern = f"{archive_path.stem}.chd"
                        chd_path = self.output_dir / chd_pattern
                        if chd_path.exists():
                            self.playlist_manager.register_disc(chd_path, update_playlists=False)
                    # Legacy tracking
                    elif base_game and disc_number:
                        if base_game not in self.processed_games:
                            self.processed_games[base_game] = []
                        if disc_number not in self.processed_games[base_game]:
                            self.processed_games[base_game].append(disc_number)
            
            logger.info(f"Archive analysis complete: {archive_path.name} - "
                       f"{analysis['complexity']} complexity, "
                       f"{analysis['size'] / (1024*1024):.1f} MB uncompressed, "
                       f"{analysis['file_count']} files")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze archive {archive_path}: {e}")
            # For failed analysis, estimate based on compressed size
            if analysis['compressed_size'] >= SIZE_THRESHOLD_MEDIUM:
                analysis['complexity'] = 'high'  # Assume high complexity if analysis fails
            else:
                analysis['complexity'] = 'medium'
            
            return analysis
    
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
    
    def calculate_optimal_workers(self, archive_analyses):
        """
        Calculate the optimal number of worker threads based on archive analyses and system resources.
        
        Args:
            archive_analyses (list): List of archive analysis results.
            
        Returns:
            dict: Mapping of complexity levels to worker counts.
        """
        # Get system resources
        resources = self.check_system_resources()
        
        # Base calculation on available memory
        available_memory_gb = resources['memory_available'] / (1024 * 1024 * 1024)
        
        # Start with user-specified max_workers, or default to CPU count
        base_workers = self.max_workers
        
        # Calculate memory-based worker limits
        # Assume each worker needs at least 1GB for minimal archives
        # Adjust based on available memory and complexity
        memory_based_minimal = max(1, int(available_memory_gb / 0.5))  # 0.5GB per minimal worker
        memory_based_low = max(1, int(available_memory_gb / 1))  # 1GB per low-complexity worker
        memory_based_medium = max(1, int(available_memory_gb / 2))  # 2GB per medium-complexity worker
        memory_based_high = max(1, int(available_memory_gb / 4))  # 4GB per high-complexity worker
        
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
        
        # Disk space check
        disk_space_gb = resources['disk_space'] / (1024 * 1024 * 1024)
        if disk_space_gb < 10:  # Less than 10GB free
            logger.warning(f"Low disk space: {disk_space_gb:.1f} GB available")
            adjustment_factor *= 0.5
        
        # Calculate and adjust workers
        workers = {
            'minimal': min(base_workers, max(1, int(memory_based_minimal * adjustment_factor))),
            'low': min(base_workers, max(1, int(memory_based_low * adjustment_factor))),
            'medium': min(base_workers // 2, max(1, int(memory_based_medium * adjustment_factor))),
            'high': 1  # High complexity archives are always processed sequentially
        }
        
        logger.info(f"Optimal workers: minimal={workers['minimal']}, low={workers['low']}, "
                  f"medium={workers['medium']}, high={workers['high']}")
        
        return workers
    
    def extract_archive(self, archive_path, target_dir=None):
        """
        Extract a single .7z archive with resource monitoring.
        
        Args:
            archive_path (str): Path to the .7z archive.
            target_dir (str, optional): Directory to extract to. Defaults to a temp directory.
            
        Returns:
            Path: Directory containing extracted files.
        """
        archive_path = Path(archive_path)
        
        # Generate a target directory if none provided
        if not target_dir:
            # Use the archive name (without extension) as the directory name
            extract_dir = self.temp_dir / archive_path.stem
        else:
            extract_dir = Path(target_dir)
        
        # Create target directory if it doesn't exist
        os.makedirs(extract_dir, exist_ok=True)
        
        logger.info(f"Extracting {archive_path} to {extract_dir}")
        
        try:
            # Check system resources before extraction
            resources = self.check_system_resources()
            
            # If memory is critically low (>90% used), wait for resources to free up
            retry_count = 0
            while resources['memory_percent'] > 90 and retry_count < 3:
                logger.warning(f"Memory usage is high ({resources['memory_percent']}%), "
                             f"waiting before extraction: {archive_path.name}")
                time.sleep(10)  # Wait 10 seconds
                resources = self.check_system_resources()
                retry_count += 1
            
            # Extract the archive
            with py7zr.SevenZipFile(archive_path, mode='r') as z:
                z.extractall(path=extract_dir)
            
            logger.info(f"Extraction successful: {archive_path}")
            return extract_dir
        
        except py7zr.exceptions.Bad7zFile as e:
            logger.error(f"Corrupt or invalid 7z file {archive_path}: {e}")
            # Clean up the target directory if extraction failed
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            raise
            
        except MemoryError:
            logger.error(f"Memory error extracting {archive_path}, likely due to insufficient RAM")
            # Clean up the target directory if extraction failed
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            raise
            
        except Exception as e:
            logger.error(f"Failed to extract {archive_path}: {e}")
            # Clean up the target directory if extraction failed
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            raise
    
    def extract_multiple(self, archive_paths, target_dir=None):
        """
        Extract multiple .7z archives with adaptive worker allocation and resume functionality.
        
        Args:
            archive_paths (list): List of paths to .7z archives.
            target_dir (str, optional): Base directory for extraction. Defaults to temp directory.
            
        Returns:
            dict: Mapping of archive paths to their extracted directories.
        """
        target_base = Path(target_dir) if target_dir else self.temp_dir
        os.makedirs(target_base, exist_ok=True)
        
        results = {}
        
        # First, analyze all archives to determine which ones can be skipped
        logger.info(f"Analyzing {len(archive_paths)} archives...")
        archive_analyses = [self.analyze_archive(archive) for archive in archive_paths]
        
        # Group archives by complexity and skippability
        minimal_complexity = []
        low_complexity = []
        medium_complexity = []
        high_complexity = []
        skippable = []
        
        # Group by game series for efficient processing and M3U creation
        game_series = {}
        
        for analysis in archive_analyses:
            # Track for M3U creation if it's part of a multi-disc series
            if analysis['base_game'] and analysis['disc_number']:
                if analysis['base_game'] not in game_series:
                    game_series[analysis['base_game']] = []
                game_series[analysis['base_game']].append(analysis)
            
            # Sort by complexity and skippability
            if analysis['can_skip']:
                skippable.append(analysis['path'])
                
                # If this is part of a multi-disc series, check if we've now got all discs
                if analysis['base_game'] and analysis['disc_number'] and analysis['base_game'] in game_series:
                    # Check if this completes the set for this game
                    # We'll consider a series complete if we have at least 2 discs and haven't already processed it
                    series_discs = [a['disc_number'] for a in game_series[analysis['base_game']]]
                    if len(series_discs) >= 2 and analysis['base_game'] not in self.completed_game_series:
                        # Mark for immediate M3U creation
                        self._check_and_notify_series_completion(analysis['base_game'], series_discs)
            elif analysis['complexity'] == 'minimal':
                minimal_complexity.append(analysis['path'])
            elif analysis['complexity'] == 'low':
                low_complexity.append(analysis['path'])
            elif analysis['complexity'] == 'medium':
                medium_complexity.append(analysis['path'])
            else:  # high or unknown
                high_complexity.append(analysis['path'])
        
        # Log skippable archives
        if skippable:
            logger.info(f"Skipping {len(skippable)} already processed archives")
            for skip_path in skippable:
                results[skip_path] = None  # Mark as processed but no extraction dir
        
        logger.info(f"Archive complexity breakdown: "
                  f"{len(minimal_complexity)} minimal, "
                  f"{len(low_complexity)} low, "
                  f"{len(medium_complexity)} medium, "
                  f"{len(high_complexity)} high, "
                  f"{len(skippable)} skippable")
        
        # Calculate optimal workers for each complexity level
        optimal_workers = self.calculate_optimal_workers(archive_analyses)
        
        # Process archives by complexity
        # Process minimal complexity archives first (typically very small)
        if minimal_complexity:
            logger.info(f"Processing {len(minimal_complexity)} minimal complexity archives...")
            minimal_results = self._extract_batch(
                minimal_complexity, 
                target_base,
                optimal_workers['minimal']
            )
            results.update(minimal_results)
        
        # Process low complexity archives
        if low_complexity:
            logger.info(f"Processing {len(low_complexity)} low complexity archives...")
            low_results = self._extract_batch(
                low_complexity, 
                target_base,
                optimal_workers['low']
            )
            results.update(low_results)
        
        # Process medium complexity archives with fewer workers
        if medium_complexity:
            logger.info(f"Processing {len(medium_complexity)} medium complexity archives...")
            medium_results = self._extract_batch(
                medium_complexity, 
                target_base,
                optimal_workers['medium']
            )
            results.update(medium_results)
        
        # Process high complexity archives sequentially
        if high_complexity:
            logger.info(f"Processing {len(high_complexity)} high complexity archives sequentially...")
            for archive in high_complexity:
                logger.info(f"Extracting high complexity archive: {archive}")
                try:
                    # Extract high complexity archives one at a time
                    extract_dir = self.extract_archive(archive, target_base / Path(archive).stem)
                    results[archive] = extract_dir
                    
                    # After extracting a large archive, check resources
                    resources = self.check_system_resources()
                    
                    # If memory is high after extraction, wait for potential garbage collection
                    if resources['memory_percent'] > 75:
                        logger.info(f"Memory usage at {resources['memory_percent']}%, waiting briefly")
                        time.sleep(5)  # Short pause to allow resources to be reclaimed
                        
                except Exception as e:
                    logger.error(f"Extraction failed for {archive}: {e}")
                    results[archive] = None
        
        # Count successful extractions
        successful = sum(1 for path in results.values() if path is not None)
        logger.info(f"Extraction complete: {successful}/{len(archive_paths) - len(skippable)} extracted, "
                   f"{len(skippable)} skipped")
        
        return results
    
    def _extract_batch(self, archives, target_base, workers):
        """
        Extract a batch of archives with a specified number of workers.
        
        Args:
            archives (list): List of archive paths.
            target_base (Path): Base directory for extraction.
            workers (int): Number of worker threads.
            
        Returns:
            dict: Mapping of archive paths to their extracted directories.
        """
        results = {}
        
        # Limit workers to the number of archives
        effective_workers = min(workers, len(archives))
        logger.info(f"Extracting {len(archives)} archives using {effective_workers} workers")
        
        with ThreadPoolExecutor(max_workers=effective_workers) as executor:
            # Submit extraction tasks
            future_to_archive = {}
            
            for archive in archives:
                # Create a target directory based on the archive name
                target_dir = target_base / Path(archive).stem
                
                future = executor.submit(self.extract_archive, archive, target_dir)
                future_to_archive[future] = archive
            
            # Process results as they complete
            for future in future_to_archive:
                archive = future_to_archive[future]
                try:
                    results[archive] = future.result()
                    
                    # Brief pause between completions to allow resource reclamation
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Extraction failed for {archive}: {e}")
                    results[archive] = None
        
        return results
    
    def identify_disc_files(self, directory):
        """
        Identify disc image files in a directory that can be converted to CHD.
        Also tracks game information for M3U creation.
        
        Args:
            directory (str): Directory to search.
            
        Returns:
            list: List of tuples (file_path, file_type) for convertible files.
        """
        directory = Path(directory)
        convertible_files = []
        
        # Extensions that can be converted to CHD
        supported_extensions = {
            '.iso': 'iso',
            '.bin': 'bin',
            '.img': 'img',
            '.cue': 'cue',
            '.gdi': 'gdi',
            '.toc': 'toc',
            '.nrg': 'nrg',
            '.cdi': 'cdi'
        }
        
        logger.debug(f"Searching for disc files in {directory}")
        
        # Create a dictionary to track cue files and their related bin files
        cue_files = {}
        bin_files = []
        other_files = []
        
        # First pass: categorize files
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = Path(root) / file
                extension = file_path.suffix.lower()
                
                if extension in supported_extensions:
                    # Check if this file would already have a corresponding CHD in the output directory
                    if self.output_dir:
                        chd_path = self.output_dir / (file_path.stem + ".chd")
                        if chd_path.exists():
                            logger.debug(f"Skipping already converted file: {file_path}")
                            
                            # Register with PlaylistManager if available
                            if self.playlist_manager:
                                self.playlist_manager.register_disc(chd_path, update_playlists=False)
                            # Legacy tracking
                            else:
                                base_game, disc_num = self._extract_game_info(file_path.stem)
                                if base_game and disc_num:
                                    if base_game not in self.processed_games:
                                        self.processed_games[base_game] = []
                                    if disc_num not in self.processed_games[base_game]:
                                        self.processed_games[base_game].append(disc_num)
                            
                            continue
                    
                    # Categorize by file type
                    if extension == '.cue':
                        # Store the cue file with its parent directory as key
                        parent_dir = file_path.parent
                        if parent_dir not in cue_files:
                            cue_files[parent_dir] = []
                        cue_files[parent_dir].append(file_path)
                    elif extension == '.bin':
                        bin_files.append(file_path)
                    else:
                        other_files.append((file_path, supported_extensions[extension]))
        
        # Second pass: prioritize cue files over individual bin files
        for parent_dir, cues in cue_files.items():
            # Add all cue files
            for cue_file in cues:
                convertible_files.append((cue_file, 'cue'))
                
                # Register with PlaylistManager if available
                base_game, disc_num = self._extract_game_info(cue_file.stem)
                if base_game and disc_num:
                    # We can't register the CHD yet as it doesn't exist, but we can track 
                    # the information for legacy compatibility
                    if self.playlist_manager:
                        # Will be handled during conversion
                        pass
                    # Legacy tracking
                    else:
                        if base_game not in self.processed_games:
                            self.processed_games[base_game] = []
                        if disc_num not in self.processed_games[base_game]:
                            self.processed_games[base_game].append(disc_num)
                
                logger.debug(f"Found cue file: {cue_file}")
            
            # Track bin files that are in this directory to exclude them later
            covered_bins = []
            for bin_file in bin_files:
                if bin_file.parent == parent_dir:
                    covered_bins.append(bin_file)
            
            # Remove covered bin files from the bin_files list
            for bin_file in covered_bins:
                bin_files.remove(bin_file)
        
        # Add remaining bin files that weren't covered by cue files
        for bin_file in bin_files:
            convertible_files.append((bin_file, 'bin'))
            
            # Track for M3U creation
            base_game, disc_num = self._extract_game_info(bin_file.stem)
            if base_game and disc_num:
                # We can't register the CHD yet as it doesn't exist, but we can track 
                # the information for legacy compatibility
                if self.playlist_manager:
                    # Will be handled during conversion
                    pass
                # Legacy tracking
                else:
                    if base_game not in self.processed_games:
                        self.processed_games[base_game] = []
                    if disc_num not in self.processed_games[base_game]:
                        self.processed_games[base_game].append(disc_num)
                    
            logger.debug(f"Found bin file (not covered by cue): {bin_file}")
        
        # Add other convertible files
        for file_path, file_type in other_files:
            convertible_files.append((file_path, file_type))
            
            # Track for M3U creation
            base_game, disc_num = self._extract_game_info(file_path.stem)
            if base_game and disc_num:
                # We can't register the CHD yet as it doesn't exist, but we can track 
                # the information for legacy compatibility
                if self.playlist_manager:
                    # Will be handled during conversion
                    pass
                # Legacy tracking
                else:
                    if base_game not in self.processed_games:
                        self.processed_games[base_game] = []
                    if disc_num not in self.processed_games[base_game]:
                        self.processed_games[base_game].append(disc_num)
        
        logger.info(f"Found {len(convertible_files)} convertible files in {directory}")
        return convertible_files
    
    def get_processed_games(self):
        """
        Get information about processed games for M3U creation.
        
        Returns:
            dict: Mapping of game base names to lists of disc numbers.
        """
        return self.processed_games
    
    def mark_game_series_complete(self, base_game):
        """
        Mark a game series as complete for M3U creation.
        
        Args:
            base_game (str): Base name of the game.
        """
        if base_game in self.processed_games:
            self.completed_game_series.add(base_game)
            logger.debug(f"Marked game series as complete: {base_game}")
    
    def get_completed_series(self):
        """
        Get the set of completed game series.
        
        Returns:
            set: Set of completed game series base names.
        """
        return self.completed_game_series
    
    def process_archive_series(self):
        """
        Process any completed series that need M3U files created.
        Called at appropriate intervals to ensure M3U files are created timely.
        
        Returns:
            int: Number of series processed.
        """
        processed_count = 0
        
        # If using PlaylistManager, let it handle the playlist creation
        if self.playlist_manager and self.output_dir:
            # We need to check each series for completeness and update playlists if needed
            # This is now handled in batch during final processing
            return 0
            
        # Legacy implementation
        # Check all game series to see if any are complete
        processed_games = self.get_processed_games()
        for base_game, disc_numbers in processed_games.items():
            # Check if this is a multi-disc series that hasn't been processed yet
            if len(disc_numbers) >= 2 and base_game not in self.completed_game_series:
                # Check if we have all expected discs
                max_disc = max(disc_numbers)
                is_complete = all(i in disc_numbers for i in range(1, max_disc + 1))
                
                # Only create a playlist if we have a complete series or just processed the highest disc
                if is_complete:
                    self._check_and_notify_series_completion(base_game, disc_numbers)
                    processed_count += 1
                
        return processed_count
    
    def _check_and_notify_series_completion(self, base_game, disc_numbers):
        """
        Check if a game series is complete and create M3U if needed.
        
        Args:
            base_game (str): Base name of the game series.
            disc_numbers (list): List of disc numbers in the series.
        """
        # A series is considered complete if it has at least 2 discs
        if len(disc_numbers) >= 2 and base_game not in self.completed_game_series:
            logger.info(f"Detected complete game series: {base_game} with discs {sorted(disc_numbers)}")
            
            # If using PlaylistManager, let it handle playlist creation
            if self.playlist_manager and self.output_dir:
                # Check if the series is complete before updating
                max_disc = max(disc_numbers)
                is_complete = all(i in disc_numbers for i in range(1, max_disc + 1))
                
                # Only update the playlist if the series is complete or we just processed the highest disc
                highest_disc_processed = max(disc_numbers)
                if is_complete or highest_disc_processed == max_disc:
                    self.playlist_manager.update_playlist(base_game)
                    self.completed_game_series.add(base_game)
                return
                
            # Legacy implementation
            # Mark as completed
            self.completed_game_series.add(base_game)
            
            # Immediately notify other components that a series is complete
            # This simplifies timing of M3U creation
            logger.info(f"Marking game series for M3U creation: {base_game}")
            
            # Store in processed_games for M3U creation
            if base_game not in self.processed_games:
                self.processed_games[base_game] = []
            for disc_num in disc_numbers:
                if disc_num not in self.processed_games[base_game]:
                    self.processed_games[base_game].append(disc_num)
    
    def cleanup(self):
        """Clean up temporary files."""
        logger.info(f"Cleaning up temporary files in {self.temp_dir}")
        
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            logger.info("Cleanup successful")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

# Main function for testing
if __name__ == "__main__":
    # Set up logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    import sys
    
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <7z_file>")
        sys.exit(1)
    
    # Test extraction
    extractor = Extractor()
    
    # Analyze the archive first
    analysis = extractor.analyze_archive(sys.argv[1])
    print(f"Archive analysis: {analysis}")
    
    # Extract based on complexity
    extracted_dir = extractor.extract_archive(sys.argv[1])
    
    print(f"Extracted to: {extracted_dir}")
    
    # Find convertible files
    convertible_files = extractor.identify_disc_files(extracted_dir)
    
    print("Convertible files:")
    for file_path, file_type in convertible_files:
        print(f"  {file_path} (type: {file_type})")
    
    # Don't clean up in test mode to allow inspection
    print("Skipping cleanup for testing")