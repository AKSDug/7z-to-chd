def scan_output_directory(self):
        """
        Scan the output directory for CHD files and find multi-disc games 
        that need M3U playlists. Creates M3Us for any found series.
        
        Returns:
            int: Number of M3U playlists created
        """
        if not self.output_dir or not self.output_dir.exists():
            logger.warning("Output directory not set or doesn't exist")
            return 0
        
        # Get all CHD files
        chd_files = list(self.output_dir.glob("*.chd"))
        logger.debug(f"Found {len(chd_files)} CHD files in output directory")
        
        # Identify multi-disc games
        multi_disc_games = self.identify_multi_disc_games(chd_files)
        
        # Create M3U playlists for all identified games
        m3u_files = self.create_all_playlists(multi_disc_games)
        
        logger.info(f"Created {len(m3u_files)} M3U playlists from directory scan")
        return len(m3u_files)#!/usr/bin/env python3
"""
7z-to-CHD Converter - Enhanced Playlist Module
Handles the creation of .m3u playlists for multi-disk games
with improved resume handling and completion timing

Author: AKSDug
Repository: https://github.com/AKSDug/7z-to-chd
"""

import os
import logging
import re
from pathlib import Path
from collections import defaultdict

# Set up logging
logger = logging.getLogger('playlist')

class PlaylistGenerator:
    """Class for handling creation of .m3u playlists for multi-disk games with improved timing."""
    
    def __init__(self, output_dir=None):
        """
        Initialize the playlist generator.
        
        Args:
            output_dir (str, optional): Output directory where CHD files are stored.
        """
        # Common disc identifier patterns
        self.disc_patterns = [
            r'(?i)[\[(]?disc\s*(\d+)[\])]?',            # (Disc 1), [Disc 2], Disc 3
            r'(?i)[\[(]?cd\s*(\d+)[\])]?',              # (CD 1), [CD 2], CD 3
            r'(?i)[\[(]?disk\s*(\d+)[\])]?',            # (Disk 1), [Disk 2], Disk 3
            r'(?i)[\[(]?volume\s*(\d+)[\])]?',          # (Volume 1), [Volume 2]
            r'(?i)[\[(]?vol\s*(\d+)[\])]?',             # (Vol 1), [Vol 2]
            r'(?i)[\[(]?d(\d+)[\])]?',                  # (D1), [D2], D3
            r'(?i)[\s\-\_\.]+d(\d+)[\s\-\_\.]?',        # Game - D1, Game_D2, Game.D3
            r'[\s\-\_\.]+(\d+)[\s\-\_\.]?'              # Game - 1, Game_2, Game.3
        ]
        
        self.output_dir = Path(output_dir) if output_dir else None
        self.created_m3us = set()  # Track which M3U files we've already created
        
        logger.debug("PlaylistGenerator initialized")
    
    def set_output_directory(self, output_dir):
        """
        Set the output directory for CHD and M3U files.
        
        Args:
            output_dir (str): Path to output directory.
        """
        self.output_dir = Path(output_dir)
        logger.debug(f"Output directory set to {self.output_dir}")
        
        # Check for existing M3U files to avoid recreating them
        if self.output_dir and self.output_dir.exists():
            for m3u_file in self.output_dir.glob("*.m3u"):
                self.created_m3us.add(m3u_file.stem)
                logger.debug(f"Found existing M3U: {m3u_file.name}")
    
    def _extract_base_name_and_disc(self, filename):
        """
        Extract the base name and disc number from a filename.
        
        Args:
            filename (str): Filename to parse.
            
        Returns:
            tuple: (base_name, disc_number) or (filename, None) if no disc pattern found.
        """
        # Strip extension
        name = Path(filename).stem
        
        # Try to match disc patterns
        for pattern in self.disc_patterns:
            match = re.search(pattern, name)
            if match:
                disc_num = int(match.group(1))
                # Remove the disc information from the name
                base_name = re.sub(pattern, '', name).strip(' -_.')
                return base_name, disc_num
        
        # No disc pattern found
        return name, None
    
    def identify_multi_disc_games(self, chd_files):
        """
        Identify multi-disc games from a list of CHD files.
        
        Args:
            chd_files (list): List of CHD file paths.
            
        Returns:
            dict: Dictionary mapping base names to lists of (file_path, disc_number) tuples.
        """
        games = defaultdict(list)
        
        for file_path in chd_files:
            file_path = Path(file_path)
            filename = file_path.name
            
            # Extract base name and disc number
            base_name, disc_num = self._extract_base_name_and_disc(filename)
            
            # If this is a disc of a multi-disc game
            if disc_num is not None:
                games[base_name].append((file_path, disc_num))
            else:
                # Single disc game, use the filename as key
                games[filename].append((file_path, 1))
        
        # Filter out single-disc games
        multi_disc_games = {k: v for k, v in games.items() if len(v) > 1}
        
        logger.info(f"Identified {len(multi_disc_games)} multi-disc games")
        for game, discs in multi_disc_games.items():
            logger.debug(f"Multi-disc game: {game} ({len(discs)} discs)")
            for path, disc_num in discs:
                logger.debug(f"  Disc {disc_num}: {path}")
        
        return multi_disc_games
    
    def create_m3u_playlist(self, base_name, disc_files, output_dir=None):
        """
        Create an .m3u playlist for a multi-disc game.
        
        Args:
            base_name (str): Base name of the game.
            disc_files (list): List of (file_path, disc_number) tuples.
            output_dir (str, optional): Directory to save the .m3u file. Defaults to self.output_dir.
            
        Returns:
            Path: Path to the created .m3u file.
        """
        # Determine output directory
        output_dir = Path(output_dir) if output_dir else self.output_dir
        if not output_dir:
            logger.error("Output directory not set for M3U creation")
            return None
            
        os.makedirs(output_dir, exist_ok=True)
        
        # Clean base name for filename
        clean_name = re.sub(r'[<>:"/\\|?*]', '_', base_name)
        m3u_path = output_dir / f"{clean_name}.m3u"
        
        # Check if this M3U already exists
        if m3u_path.exists() or clean_name in self.created_m3us:
            logger.info(f"M3U playlist already exists: {m3u_path}")
            self.created_m3us.add(clean_name)
            return m3u_path
        
        logger.info(f"Creating M3U playlist: {m3u_path}")
        
        try:
            # Sort discs by number
            sorted_discs = sorted(disc_files, key=lambda x: x[1])
            
            with open(m3u_path, 'w', encoding='utf-8') as f:
                # Write header comment
                f.write(f"# {base_name} - Multi-disc game playlist\n")
                f.write("# Created by 7z-to-CHD Converter\n")
                f.write("#\n")
                
                # Write disc entries
                for file_path, disc_num in sorted_discs:
                    # Use relative paths if files are in the same directory as the M3U
                    if file_path.parent == output_dir:
                        # Write only the filename
                        f.write(f"{file_path.name}\n")
                    else:
                        # Write the absolute path
                        f.write(f"{file_path}\n")
            
            logger.info(f"M3U playlist created successfully: {m3u_path}")
            self.created_m3us.add(clean_name)
            return m3u_path
        
        except Exception as e:
            logger.error(f"Failed to create M3U playlist: {e}")
            return None
    
    def create_all_playlists(self, multi_disc_games, output_dir=None):
        """
        Create .m3u playlists for all identified multi-disc games.
        
        Args:
            multi_disc_games (dict): Dictionary mapping base names to lists of (file_path, disc_number) tuples.
            output_dir (str, optional): Directory to save the .m3u files. Defaults to self.output_dir.
            
        Returns:
            list: List of created .m3u file paths.
        """
        # Determine output directory
        output_dir = Path(output_dir) if output_dir else self.output_dir
        if not output_dir:
            logger.error("Output directory not set for M3U creation")
            return []
            
        os.makedirs(output_dir, exist_ok=True)
        
        m3u_files = []
        
        logger.info(f"Creating M3U playlists for {len(multi_disc_games)} games")
        
        for base_name, disc_files in multi_disc_games.items():
            # Skip if we've already created this M3U
            clean_name = re.sub(r'[<>:"/\\|?*]', '_', base_name)
            if clean_name in self.created_m3us:
                logger.debug(f"Skipping already created M3U for {base_name}")
                continue
                
            m3u_path = self.create_m3u_playlist(base_name, disc_files, output_dir)
            if m3u_path:
                m3u_files.append(m3u_path)
        
        logger.info(f"Created {len(m3u_files)} M3U playlists")
        return m3u_files
    
    def create_m3u_for_game_series(self, base_game, output_dir=None):
        """
        Create an M3U playlist for a specific game series by finding matching CHD files.
        
        Args:
            base_game (str): Base name of the game series.
            output_dir (str, optional): Directory to look for CHD files and save the M3U.
                                        Defaults to self.output_dir.
        
        Returns:
            bool: True if M3U was created, False otherwise.
        """
        # Determine output directory
        output_dir = Path(output_dir) if output_dir else self.output_dir
        if not output_dir:
            logger.error("Output directory not set for M3U creation")
            return False
            
        # Clean base name for filename and check if already created
        clean_name = re.sub(r'[<>:"/\\|?*]', '_', base_game)
        if clean_name in self.created_m3us:
            logger.debug(f"M3U already created for {base_game}")
            return False
            
        # Check if M3U file already exists
        m3u_path = output_dir / f"{clean_name}.m3u"
        if m3u_path.exists():
            logger.info(f"M3U playlist already exists: {m3u_path}")
            self.created_m3us.add(clean_name)
            return True
        
        # Find matching CHD files for this game series
        disc_files = []
        for chd_file in output_dir.glob("*.chd"):
            file_base_game, disc_num = self._extract_base_name_and_disc(chd_file.stem)
            if file_base_game == base_game and disc_num is not None:
                disc_files.append((chd_file, disc_num))
        
        # Check if we found multiple discs
        if len(disc_files) <= 1:
            logger.debug(f"Not enough discs found for {base_game}, skipping M3U creation")
            return False
        
        # Create the M3U playlist
        logger.info(f"Creating M3U playlist for {base_game} with {len(disc_files)} discs")
        m3u_path = self.create_m3u_playlist(base_game, disc_files, output_dir)
        
        return m3u_path is not None
    
    def check_for_incomplete_series(self, expected_disc_count=3):
        """
        Check for incomplete game series where only some discs are present and create M3Us.
        This is useful when a series doesn't have all discs but would still benefit from an M3U.
        
        Args:
            expected_disc_count (int, optional): Expected maximum number of discs to check for.
                                               Defaults to 3.
        
        Returns:
            int: Number of M3U playlists created for incomplete series.
        """
        if not self.output_dir or not self.output_dir.exists():
            logger.warning("Output directory not set or doesn't exist")
            return 0
        
        # Maps to track game series discs
        game_series = defaultdict(set)
        
        # Scan for CHD files and extract game series information
        for chd_file in self.output_dir.glob("*.chd"):
            base_game, disc_num = self._extract_base_name_and_disc(chd_file.stem)
            if base_game and disc_num:
                game_series[base_game].add(disc_num)
        
        # Check for multi-disc games that don't have all possible discs
        created_count = 0
        for base_game, disc_nums in game_series.items():
            # If we have at least 2 discs but less than the expected count
            if len(disc_nums) >= 2 and len(disc_nums) < expected_disc_count:
                # Check if we have disc 1 and disc 2 at minimum (common scenario)
                if 1 in disc_nums and 2 in disc_nums:
                    clean_name = re.sub(r'[<>:"/\\|?*]', '_', base_game)
                    if clean_name not in self.created_m3us:
                        if self.create_m3u_for_game_series(base_game):
                            logger.info(f"Created M3U for incomplete series: {base_game} (discs: {sorted(disc_nums)})")
                            created_count += 1
        
        return created_count

# Main function for testing
if __name__ == "__main__":
    # Set up logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Create M3U playlists for multi-disc games')
    parser.add_argument('directory', help='Directory containing CHD files')
    parser.add_argument('--output', '-o', help='Output directory for M3U files', default=None)
    parser.add_argument('--check-incomplete', '-c', action='store_true', 
                      help='Check for incomplete series and create M3Us if possible')
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    output_dir = Path(args.output) if args.output else directory
    
    # Get all CHD files in the directory
    chd_files = list(directory.glob('*.chd'))
    
    print(f"Found {len(chd_files)} CHD files in {directory}")
    
    # Create playlist generator
    generator = PlaylistGenerator(output_dir)
    
    # Identify multi-disc games
    multi_disc_games = generator.identify_multi_disc_games(chd_files)
    
    print(f"Identified {len(multi_disc_games)} multi-disc games")
    
    # Create M3U playlists
    m3u_files = generator.create_all_playlists(multi_disc_games)
    
    print(f"Created {len(m3u_files)} M3U playlists in {output_dir}")
    
    # Check for incomplete series if requested
    if args.check_incomplete:
        incomplete_count = generator.check_for_incomplete_series()
        print(f"Created {incomplete_count} M3U playlists for incomplete series")