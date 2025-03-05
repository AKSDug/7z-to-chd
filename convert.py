#!/usr/bin/env python3
"""
7z-to-CHD Converter - Main Script
Batch processing of .7z archives to CHD format

Author: AKSDug
Repository: https://github.com/AKSDug/7z-to-chd
"""

import os
import sys
import argparse
import logging
import multiprocessing
import shutil
import re  # Import regex module
from pathlib import Path
import colorama
from tqdm import tqdm

# Initialize colorama
colorama.init()

# Add parent directory to path for importing local modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import local modules
from lib.extractor import Extractor
from lib.converter import Converter
from lib.playlist import PlaylistManager
from lib.utils import setup_logging, Timer, confirm_path

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Batch convert .7z archives to CHD format with multi-disc support',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('--source', '-s', help='Source directory containing .7z files')
    parser.add_argument('--destination', '-d', help='Destination directory for CHD and .m3u files')
    parser.add_argument('--keep', '-k', choices=['yes', 'no'], help='Keep original files after conversion')
    parser.add_argument('--threads', '-t', type=int, help='Maximum number of concurrent operations (0 for CPU count)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--state-file', help='Path to playlist state file (for resuming interrupted conversions)')
    parser.add_argument('--skip-playlist-scan', action='store_true', help='Skip initial scan for existing playlists')
    
    return parser.parse_args()

def prompt_user_input(args):
    """Prompt the user for input if not provided as arguments."""
    print(f"{colorama.Fore.CYAN}7z-to-CHD Converter{colorama.Style.RESET_ALL}")
    print("Batch conversion of .7z archives to CHD format with multi-disc support")
    print()
    
    # Source directory
    if args.source:
        source_dir = args.source
    else:
        print("Enter the source directory containing .7z files:")
        source_dir = input("> ").strip()
    
    # Validate source directory
    try:
        source_dir = confirm_path(source_dir)
        print(f"{colorama.Fore.GREEN}✓ Source directory: {source_dir}{colorama.Style.RESET_ALL}")
    except (FileNotFoundError, NotADirectoryError) as e:
        print(f"{colorama.Fore.RED}Error: {e}{colorama.Style.RESET_ALL}")
        sys.exit(1)
    
    # Destination directory
    if args.destination:
        dest_dir = args.destination
    else:
        print("\nEnter the destination directory for CHD and .m3u files:")
        dest_dir = input("> ").strip()
    
    # Validate and create destination directory if needed
    try:
        dest_dir = confirm_path(dest_dir, create=True)
        print(f"{colorama.Fore.GREEN}✓ Destination directory: {dest_dir}{colorama.Style.RESET_ALL}")
    except NotADirectoryError as e:
        print(f"{colorama.Fore.RED}Error: {e}{colorama.Style.RESET_ALL}")
        sys.exit(1)
    
    # Keep or delete original files
    if args.keep:
        keep_files = args.keep == 'yes'
    else:
        print("\nKeep original files after conversion? (yes/no):")
        keep_input = input("> ").strip().lower()
        keep_files = keep_input in ['yes', 'y', 'true', '1']
    
    keep_str = "Yes" if keep_files else "No"
    print(f"{colorama.Fore.GREEN}✓ Keep original files: {keep_str}{colorama.Style.RESET_ALL}")
    
    # Multithreading limitations
    if args.threads is not None:
        max_workers = args.threads
    else:
        cpu_count = multiprocessing.cpu_count()
        print(f"\nEnter maximum number of concurrent operations (0 for CPU count: {cpu_count}):")
        try:
            max_workers = int(input("> ").strip())
        except ValueError:
            max_workers = 0
    
    if max_workers <= 0:
        max_workers = multiprocessing.cpu_count()
    
    print(f"{colorama.Fore.GREEN}✓ Maximum worker threads: {max_workers}{colorama.Style.RESET_ALL}")
    print()
    
    # State file for persistent playlist state
    state_file = args.state_file
    
    # Skip playlist scan option
    skip_playlist_scan = args.skip_playlist_scan
    
    return source_dir, dest_dir, keep_files, max_workers, state_file, skip_playlist_scan

def find_7z_files(source_dir):
    """Find all .7z files in the source directory."""
    logger = logging.getLogger('main')
    logger.info(f"Searching for .7z files in {source_dir}")
    
    files = list(source_dir.glob('**/*.7z'))
    logger.info(f"Found {len(files)} .7z files")
    
    return files

def batch_process(source_dir, dest_dir, keep_files, max_workers, state_file=None, skip_playlist_scan=False, temp_dir=None):
    """Process all .7z files in the source directory."""
    logger = logging.getLogger('main')
    timer = Timer().start()
    
    # Initialize PlaylistManager with state file
    playlist_manager = PlaylistManager(output_dir=dest_dir, state_file=state_file)
    
    # Initialize components with cross-references
    extractor = Extractor(temp_dir=temp_dir, max_workers=max_workers, output_dir=dest_dir)
    converter = Converter(max_workers=max_workers)
    
    # Connect components for optimal coordination
    extractor.set_playlist_manager(playlist_manager)
    converter.set_extractor(extractor)
    converter.set_playlist_manager(playlist_manager)
    
    # Perform an initial scan for existing playlists if not skipped
    if not skip_playlist_scan:
        print(f"{colorama.Fore.YELLOW}Scanning for existing multi-disc games...{colorama.Style.RESET_ALL}")
        playlist_manager.scan_directory(update_all=False)
    
    # Find .7z files
    archive_files = find_7z_files(source_dir)
    
    if not archive_files:
        logger.warning("No .7z files found in the source directory")
        return {
            'archives_found': 0,
            'archives_processed': 0,
            'games_converted': 0,
            'playlists_created': 0,
            'elapsed_time': timer.elapsed()
        }
    
    # Estimate unique game count (for more accurate progress reporting)
    unique_games = set()
    for archive in archive_files:
        # Extract base game name by removing common disc identifiers
        base_name = archive.stem
        for pattern in [r'\s*\(Disc \d+\)', r'\s*\(CD\d+\)', r'\s*\(Disk \d+\)', r'\s*\(Track \d+\)']:
            base_name = re.sub(pattern, '', base_name, flags=re.IGNORECASE)
        unique_games.add(base_name)
    
    logger.info(f"Found approximately {len(unique_games)} unique games in {len(archive_files)} archives")
    
    # Process archives
    print(f"{colorama.Fore.YELLOW}Processing {len(archive_files)} archives...{colorama.Style.RESET_ALL}")
    
    # Track conversion results
    conversion_results = {}
    converted_chd_files = []
    
    # Process each archive
    for i, archive_path in enumerate(tqdm(archive_files, desc="Archives", unit="file")):
        archive_name = archive_path.name
        logger.info(f"Processing archive {i+1}/{len(archive_files)}: {archive_name}")
        
        try:
            # Pre-check if we can skip processing (if CHD already exists)
            base_game, disc_num = extractor._extract_game_info(archive_path.stem)
            chd_name = f"{archive_path.stem}.chd"
            chd_path = dest_dir / chd_name
            
            if chd_path.exists():
                logger.info(f"Skipping {archive_name} - CHD already exists: {chd_name}")
                
                # Register with PlaylistManager
                if base_game and disc_num:
                    # Register the disc without forcing a full directory scan
                    # This keeps track of the disc but doesn't update playlists yet
                    playlist_manager.register_disc(chd_path, update_playlists=False)
                
                continue
            
            # Extract archive
            extract_dir = extractor.extract_archive(archive_path)
            
            # Skip if extraction was skipped (already converted)
            if extract_dir is None:
                logger.info(f"Skipped extraction of {archive_name} (already converted)")
                continue
            
            # Find convertible files
            convertible_files = extractor.identify_disc_files(extract_dir)
            
            if not convertible_files:
                logger.warning(f"No convertible files found in {archive_name}")
                continue
            
            # Convert files
            conversion_result = converter.convert_multiple(convertible_files, dest_dir)
            
            # Ensure conversion_result is not None before trying to use it
            if conversion_result is None:
                conversion_result = {}
                
            conversion_results[archive_path] = conversion_result
            
            # Collect successful CHD conversions
            for input_file, result_tuple in conversion_result.items():
                if result_tuple is not None:  # Make sure the tuple exists
                    output_file, success = result_tuple
                    if success and output_file:
                        converted_chd_files.append(output_file)
            
            # Clean up extracted files
            if extract_dir and extract_dir.exists():
                logger.debug(f"Cleaning up extraction directory: {extract_dir}")
                shutil.rmtree(extract_dir)
            
            # Delete original archive if requested
            if not keep_files:
                logger.info(f"Deleting original archive: {archive_path}")
                archive_path.unlink()
        
        except Exception as e:
            logger.error(f"Failed to process archive {archive_name}: {e}", exc_info=True)
    
    # Create M3U playlists for multi-disc games
    print(f"{colorama.Fore.YELLOW}Creating playlists for multi-disc games...{colorama.Style.RESET_ALL}")
    
    # Scan for any newly added discs and create playlists
    # Force the update to regenerate all playlists for completeness
    playlist_count = len(playlist_manager.scan_directory(update_all=True))
    
    # Make sure we check for any incomplete series too, with a full scan
    incomplete_playlist_count = len(playlist_manager.check_for_incomplete_series(force_scan=True))
    
    # Clean up
    print(f"{colorama.Fore.YELLOW}Cleaning up...{colorama.Style.RESET_ALL}")
    extractor.cleanup()
    converter.cleanup()
    playlist_manager.cleanup()  # This saves the state before cleanup
    
    # Gather statistics
    timer.stop()
    
    total_archives = len(archive_files)
    processed_archives = sum(1 for results in conversion_results.values() if results)
    converted_files = 0
    for results in conversion_results.values():
        for _, result_tuple in results.items():
            if result_tuple and result_tuple[1]:  # Check if conversion was successful
                converted_files += 1
                
    created_playlists = playlist_count + incomplete_playlist_count
    
    # Get series status information for reporting
    series_status = playlist_manager.get_series_status()
    complete_series = sum(1 for info in series_status.values() if info['is_complete'])
    incomplete_series = sum(1 for info in series_status.values() 
                           if not info['is_complete'] and info['disc_count'] > 1)
    
    return {
        'archives_found': total_archives,
        'archives_processed': processed_archives,
        'files_converted': converted_files,
        'playlists_created': created_playlists,
        'complete_series': complete_series,
        'incomplete_series': incomplete_series,
        'elapsed_time': timer.elapsed()
    }

def display_summary(statistics):
    """Display a summary of the conversion process."""
    # Calculate success rates
    archives_success_rate = 0
    if statistics['archives_found'] > 0:
        archives_success_rate = (statistics['archives_processed'] / statistics['archives_found']) * 100
    
    # Format elapsed time
    from lib.utils import format_time
    elapsed_time = format_time(statistics['elapsed_time'])
    
    # Print summary
    print("\n" + "="*60)
    print(f"{colorama.Fore.CYAN}Conversion Summary{colorama.Style.RESET_ALL}")
    print("="*60)
    print(f"Archives found:      {statistics['archives_found']}")
    print(f"Archives processed:  {statistics['archives_processed']} ({archives_success_rate:.1f}%)")
    print(f"Files converted:     {statistics['files_converted']}")
    print(f"Playlists created:   {statistics['playlists_created']}")
    
    if 'complete_series' in statistics:
        print(f"Complete series:     {statistics['complete_series']}")
    if 'incomplete_series' in statistics:
        print(f"Incomplete series:   {statistics['incomplete_series']}")
        
    print(f"Total time:          {elapsed_time}")
    print("="*60)
    
    # Print completion message
    if statistics['archives_processed'] > 0:
        print(f"\n{colorama.Fore.GREEN}Conversion completed successfully!{colorama.Style.RESET_ALL}")
    else:
        print(f"\n{colorama.Fore.RED}No archives were successfully processed.{colorama.Style.RESET_ALL}")
        print("Check the log file for details.")

def main():
    """Main function."""
    # Parse command-line arguments
    args = parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level=log_level)
    logger = logging.getLogger('main')
    
    try:
        # Get user input
        source_dir, dest_dir, keep_files, max_workers, state_file, skip_playlist_scan = prompt_user_input(args)
        
        # Process files
        statistics = batch_process(source_dir, dest_dir, keep_files, max_workers, state_file, skip_playlist_scan)
        
        # Display summary
        display_summary(statistics)
        
    except KeyboardInterrupt:
        print(f"\n{colorama.Fore.YELLOW}Process interrupted by user.{colorama.Style.RESET_ALL}")
        logger.warning("Process interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n{colorama.Fore.RED}Error: {e}{colorama.Style.RESET_ALL}")
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)
    
    # Reset colorama
    colorama.deinit()

if __name__ == "__main__":
    main()