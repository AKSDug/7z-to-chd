#!/usr/bin/env python3
"""
7z-to-CHD Converter - Enhanced PlaylistManager Module
Handles the creation and management of .m3u playlists for multi-disc games
with improved persistence, disc detection, and incremental updates

Author: AKSDug
Repository: https://github.com/AKSDug/7z-to-chd
"""

import os
import logging
import re
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional, Union

# Set up logging
logger = logging.getLogger("playlist")


class PlaylistManager:
    """
    Enhanced class for handling creation and management of .m3u playlists for multi-disc games.

    Features:
    - Persistent state tracking between sessions
    - Dynamic playlist generation responding to newly discovered discs
    - Intelligent series detection with enhanced pattern matching
    - Incremental playlist updates preserving user customizations
    """

    def __init__(
        self,
        output_dir: Optional[Union[str, Path]] = None,
        state_file: Optional[Union[str, Path]] = None,
    ):
        """
        Initialize the playlist manager.

        Args:
            output_dir: Output directory where CHD files and M3U playlists are stored
            state_file: Path to JSON file for persisting playlist state between sessions
        """
        # Common disc identifier patterns (extended for better matching)
        self.disc_patterns = [
            r"(?i)[\[(]?disc\s*(\d+)[\])]?",  # (Disc 1), [Disc 2], Disc 3
            r"(?i)[\[(]?cd\s*(\d+)[\])]?",  # (CD 1), [CD 2], CD 3
            r"(?i)[\[(]?disk\s*(\d+)[\])]?",  # (Disk 1), [Disk 2], Disk 3
            r"(?i)[\[(]?volume\s*(\d+)[\])]?",  # (Volume 1), [Volume 2]
            r"(?i)[\[(]?vol\s*(\d+)[\])]?",  # (Vol 1), [Vol 2]
            r"(?i)[\[(]?d(\d+)[\])]?",  # (D1), [D2], D3
            r"(?i)[\s\-\_\.]+d(\d+)[\s\-\_\.]?",  # Game - D1, Game_D2, Game.D3
            r"(?i)[\s\-\_\.]+disc(\d+)[\s\-\_\.]?",  # Game - Disc1
            r"(?i)[\s\-\_\.]+cd(\d+)[\s\-\_\.]?",  # Game - CD1
            r"[\s\-\_\.]+(\d+)[\s\-\_\.]?",  # Game - 1, Game_2, Game.3
        ]

        # Initialize output directory
        self.output_dir = Path(output_dir) if output_dir else None

        # Initialize state file path
        if state_file:
            self.state_file = Path(state_file)
        elif output_dir:
            self.state_file = Path(output_dir) / "playlist_state.json"
        else:
            self.state_file = None

        # Initialize state dictionaries
        self.game_series = defaultdict(
            list
        )  # Maps base game name to list of (chd_path, disc_num) tuples
        self.created_playlists = set()  # Set of base game names for which M3Us have been created
        self.user_customized = set()  # Set of M3U files that contain user customizations
        self.series_signatures = {}  # Maps base game name to signature (hash) of its disc set
        self.recently_updated = (
            set()
        )  # Tracks series updated in current session to prevent redundant updates

        # Load state if available
        self._load_state()

        logger.debug("PlaylistManager initialized")

    def set_output_directory(self, output_dir: Union[str, Path]) -> None:
        """
        Set the output directory for CHD and M3U files.

        Args:
            output_dir: Path to output directory
        """
        self.output_dir = Path(output_dir)

        # Update state file path if not explicitly set
        if not self.state_file:
            self.state_file = self.output_dir / "playlist_state.json"

        logger.debug(f"Output directory set to {self.output_dir}")

        # Scan for existing M3U files to avoid overwriting them without permission
        self._scan_existing_playlists()

    def _scan_existing_playlists(self) -> None:
        """
        Scan output directory for existing M3U files and analyze them for disc information.
        This helps integrate existing playlists into our state management.
        """
        if not self.output_dir or not self.output_dir.exists():
            return

        logger.debug(f"Scanning for existing M3U playlists in {self.output_dir}")

        for m3u_file in self.output_dir.glob("*.m3u"):
            if m3u_file.is_file():
                self.created_playlists.add(m3u_file.stem)

                # Read the M3U file to extract disc information
                try:
                    chd_files = self._read_m3u_file(m3u_file)

                    # Check if this M3U contains non-standard entries or comments that might indicate user customization
                    with open(m3u_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        if "# Created by 7z-to-CHD Converter" not in content:
                            # This might be a user-created or customized playlist
                            self.user_customized.add(m3u_file.stem)
                            logger.debug(f"Found potentially user-customized M3U: {m3u_file.name}")

                        # Extract disc entries and add them to our game series tracking
                        if chd_files and len(chd_files) > 1:
                            # Try to determine base game name from filename
                            base_game = m3u_file.stem

                            # Process each file entry
                            for chd_file in chd_files:
                                chd_path = Path(chd_file)
                                # Try to extract disc number from filename
                                _, disc_num = self._extract_base_name_and_disc(chd_path.stem)

                                # Only add if we could determine a disc number
                                if disc_num:
                                    self._add_to_game_series(base_game, chd_path, disc_num)

                    logger.debug(
                        f"Analyzed existing M3U: {m3u_file.name}, found {len(chd_files)} disc entries"
                    )

                except Exception as e:
                    logger.warning(f"Error analyzing M3U file {m3u_file}: {e}")

    def _read_m3u_file(self, m3u_path: Path) -> List[str]:
        """
        Read an M3U file and extract CHD file entries.

        Args:
            m3u_path: Path to the M3U file

        Returns:
            List of CHD filenames or paths found in the M3U
        """
        chd_files = []
        try:
            with open(m3u_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue

                    # Only include CHD files
                    if line.lower().endswith(".chd"):
                        chd_files.append(line)

            return chd_files

        except Exception as e:
            logger.error(f"Error reading M3U file {m3u_path}: {e}")
            return []

    def _save_state(self) -> bool:
        """
        Save the current playlist state to a JSON file.

        Returns:
            True if state was successfully saved, False otherwise
        """
        if not self.state_file:
            logger.debug("No state file path defined, skipping state save")
            return False

        try:
            # Create serializable versions of state dictionaries
            serializable_state = {
                "game_series": {
                    game: [(str(path), disc_num) for path, disc_num in disc_list]
                    for game, disc_list in self.game_series.items()
                },
                "created_playlists": list(self.created_playlists),
                "user_customized": list(self.user_customized),
                "series_signatures": self.series_signatures,
                "last_updated": datetime.now().isoformat(),
            }

            # Create parent directory if it doesn't exist
            os.makedirs(self.state_file.parent, exist_ok=True)

            # Write state to file
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(serializable_state, f, indent=2)

            logger.debug(f"Playlist state saved to {self.state_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save playlist state: {e}")
            return False

    def _load_state(self) -> bool:
        """
        Load playlist state from a JSON file.

        Returns:
            True if state was successfully loaded, False otherwise
        """
        if not self.state_file or not self.state_file.exists():
            logger.debug("No state file found, starting with empty state")
            return False

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)

            # Restore game series data
            for game, disc_list in state_data.get("game_series", {}).items():
                self.game_series[game] = [(Path(path), disc_num) for path, disc_num in disc_list]

            # Restore set data
            self.created_playlists = set(state_data.get("created_playlists", []))
            self.user_customized = set(state_data.get("user_customized", []))

            # Restore series signatures
            self.series_signatures = state_data.get("series_signatures", {})

            # Reset recently updated set
            self.recently_updated = set()

            # Log when state was last saved
            last_updated = state_data.get("last_updated", "unknown")
            logger.debug(
                f"Loaded playlist state from {self.state_file} (last updated: {last_updated})"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to load playlist state: {e}")
            return False

    def _extract_base_name_and_disc(self, filename: str) -> Tuple[str, Optional[int]]:
        """
        Extract the base game name and disc number from a filename using enhanced pattern matching.

        Args:
            filename: Filename to parse (without extension)

        Returns:
            Tuple of (base_game_name, disc_number) or (filename, None) if no disc pattern found
        """
        # Strip extension if present
        name = Path(filename).stem

        # Try to match disc patterns
        for pattern in self.disc_patterns:
            match = re.search(pattern, name)
            if match:
                disc_num = int(match.group(1))
                # Remove the disc information from the name
                base_name = re.sub(pattern, "", name).strip(" -_.")

                # Only clean the base name by removing disc/volume identifiers
                # Do NOT remove region information or other parenthetical content
                # This ensures region information is preserved in the M3U filename

                return base_name, disc_num

        # No disc pattern found
        return name, None

    def _clean_filename(self, name: str) -> str:
        """
        Clean a string for use as a filename, replacing invalid characters.

        Args:
            name: String to clean

        Returns:
            Cleaned string safe for use in filenames
        """
        return re.sub(r'[<>:"/\\|?*]', "_", name)

    def _add_to_game_series(self, base_game: str, file_path: Path, disc_num: int) -> None:
        """
        Add a disc to a game series tracking data structure.

        Args:
            base_game: Base name of the game
            file_path: Path to the CHD file
            disc_num: Disc number
        """
        # Check if this exact disc is already tracked
        for existing_path, existing_num in self.game_series[base_game]:
            if existing_path == file_path or existing_num == disc_num:
                # Already tracking this disc
                return

        # Add new disc to tracking
        self.game_series[base_game].append((file_path, disc_num))

        # Sort disc list by disc number for consistent ordering
        self.game_series[base_game].sort(key=lambda x: x[1])

        # Update the series signature to track changes
        self._update_series_signature(base_game)

        logger.debug(f"Added disc {disc_num} to game series '{base_game}'")

    def _update_series_signature(self, base_game: str) -> str:
        """
        Update the signature (hash) for a game series based on its current disc set.
        This is used to detect changes in the disc set for efficient playlist updates.

        Args:
            base_game: Base name of the game

        Returns:
            String signature representing the current disc set
        """
        if base_game not in self.game_series:
            return ""

        # Create a signature based on sorted disc numbers and filenames
        disc_info = sorted(
            [(disc_num, path.name) for path, disc_num in self.game_series[base_game]]
        )
        signature = ":".join([f"{num}:{name}" for num, name in disc_info])

        # Store the signature
        self.series_signatures[base_game] = signature

        return signature

    def has_series_changed(self, base_game: str) -> bool:
        """
        Check if a game series has changed since the last playlist update.
        Public method that wraps the internal implementation.

        Args:
            base_game: Base name of the game

        Returns:
            True if the series has changed, False otherwise
        """
        return self._has_series_changed(base_game)

    def _has_series_changed(self, base_game: str) -> bool:
        """
        Check if a game series has changed since the last playlist update.

        Args:
            base_game: Base name of the game

        Returns:
            True if the series has changed, False otherwise
        """
        # If this series was recently updated in this session, no need to update again
        if base_game in self.recently_updated:
            return False

        # If we have no previous signature, consider it changed
        if base_game not in self.series_signatures:
            return True

        # Get the current signature
        current_signature = self._update_series_signature(base_game)

        # Compare with the stored signature
        return current_signature != self.series_signatures.get(base_game, "")

    def register_disc(
        self, chd_path: Union[str, Path], update_playlists: bool = True
    ) -> Optional[str]:
        """
        Register a CHD file as a disc and update game series tracking.
        Also proactively checks for other discs of the same game in the output directory.

        Args:
            chd_path: Path to CHD file
            update_playlists: Whether to automatically update playlists after registration

        Returns:
            Base game name if successfully registered as part of a series, None otherwise
        """
        chd_path = Path(chd_path)

        # Extract base game name and disc number
        base_game, disc_num = self._extract_base_name_and_disc(chd_path.stem)

        # If this file doesn't have a disc number, it's not part of a multi-disc series
        if not disc_num:
            logger.debug(
                f"CHD file {chd_path.name} does not appear to be part of a multi-disc series"
            )
            return None

        # Add to game series tracking
        self._add_to_game_series(base_game, chd_path, disc_num)

        # Check for additional discs in the output directory
        self._find_related_discs(base_game)

        # Check if we should update the playlist
        # Only update if we have multiple discs AND we have all expected discs
        if update_playlists and len(self.game_series[base_game]) > 1:
            # Check if we have a complete series (all disc numbers from 1 to max)
            disc_numbers = [d for _, d in self.game_series[base_game]]
            max_disc = max(disc_numbers)
            is_complete = all(i in disc_numbers for i in range(1, max_disc + 1))

            # Only update playlist if the series is complete or we are adding the final disc
            if is_complete or disc_num == max_disc:
                logger.info(
                    f"Creating/updating playlist for {base_game} - series appears complete with {len(disc_numbers)} discs"
                )
                self.update_playlist(base_game)

        # Save state
        self._save_state()

        return base_game

    def _find_related_discs(self, base_game: str) -> None:
        """
        Find all discs for a specific game in the output directory.
        This helps ensure we have a complete picture of all available discs.

        Args:
            base_game: Base name of the game
        """
        if not self.output_dir or not self.output_dir.exists():
            return

        # Standardize the base_game for pattern matching
        # Create pattern to match various disc number formats
        pattern_base = (
            base_game.replace("(", r"\(")
            .replace(")", r"\)")
            .replace("[", r"\[")
            .replace("]", r"\]")
        )

        # Patterns to match disc identifiers in filenames
        patterns = [
            f"{pattern_base}.*disc\\s*(\\d+).*\\.chd$",
            f"{pattern_base}.*cd\\s*(\\d+).*\\.chd$",
            f"{pattern_base}.*disk\\s*(\\d+).*\\.chd$",
            f"{pattern_base}.*d(\\d+).*\\.chd$",
        ]

        # Track what we've found
        found_discs = set()

        # Search for matching CHD files
        for chd_file in self.output_dir.glob("*.chd"):
            for pattern in patterns:
                match = re.search(pattern, chd_file.name, re.IGNORECASE)
                if match:
                    disc_num = int(match.group(1))

                    # Check if this disc is already tracked
                    already_tracked = False
                    for path, num in self.game_series[base_game]:
                        if path.name == chd_file.name or num == disc_num:
                            already_tracked = True
                            break

                    if not already_tracked:
                        logger.debug(
                            f"Found additional disc {disc_num} for {base_game}: {chd_file.name}"
                        )
                        self._add_to_game_series(base_game, chd_file, disc_num)
                        found_discs.add(disc_num)

                    break  # Stop checking patterns for this file

        if found_discs:
            logger.info(f"Added {len(found_discs)} previously untracked discs for {base_game}")

    def register_multiple_discs(
        self, chd_paths: List[Union[str, Path]], update_playlists: bool = True
    ) -> Dict[str, int]:
        """
        Register multiple CHD files and update game series tracking.
        Processes files more efficiently by grouping them by game series first.

        Args:
            chd_paths: List of paths to CHD files
            update_playlists: Whether to automatically update playlists after registration

        Returns:
            Dictionary mapping base game names to number of discs registered
        """
        # Group files by base game to process efficiently
        game_groups = defaultdict(list)
        nondisc_files = []

        # First pass: group files by game series
        for chd_path in chd_paths:
            path = Path(chd_path)
            base_game, disc_num = self._extract_base_name_and_disc(path.stem)

            if disc_num:
                game_groups[base_game].append((path, disc_num))
            else:
                nondisc_files.append(path)

        # Track registered games and disc counts
        registered_games = defaultdict(int)

        # Process each game series
        for base_game, discs in game_groups.items():
            # Reset the series signature to force update
            if base_game in self.series_signatures:
                del self.series_signatures[base_game]

            # Add all discs for this game series
            for path, disc_num in discs:
                self._add_to_game_series(base_game, path, disc_num)
                registered_games[base_game] += 1

            # Check for any additional discs of this game
            if len(discs) > 0:
                self._find_related_discs(base_game)

            # Determine if we have all expected discs for this series
            if update_playlists and len(self.game_series[base_game]) > 1:
                disc_numbers = [d for _, d in self.game_series[base_game]]
                max_disc = max(disc_numbers)
                is_complete = all(i in disc_numbers for i in range(1, max_disc + 1))

                # Only update the playlist if we have a complete series or just processed the highest disc
                highest_processed = max(d for _, d in discs)
                if is_complete or highest_processed == max_disc:
                    logger.info(
                        f"Creating/updating playlist for {base_game} - {len(disc_numbers)} discs found"
                    )
                    self.update_playlist(base_game)

        # Process non-disc files individually (unlikely to be part of series)
        for path in nondisc_files:
            # These shouldn't be part of series, but process them for completeness
            base_game, disc_num = self._extract_base_name_and_disc(path.stem)
            if disc_num:  # Just in case our earlier logic missed something
                self._add_to_game_series(base_game, path, disc_num)
                registered_games[base_game] += 1

        # Save state
        self._save_state()

        return registered_games

    def update_playlist(self, base_game: str) -> Optional[Path]:
        """
        Create or update an M3U playlist for a game series.
        Only updates if the series content has changed since last update.

        Args:
            base_game: Base name of the game series

        Returns:
            Path to the created/updated M3U file, or None if creation failed
        """
        if not self.output_dir:
            logger.error("Output directory not set, cannot create playlist")
            return None

        if base_game not in self.game_series or len(self.game_series[base_game]) <= 1:
            logger.debug(f"Not enough discs for game '{base_game}', skipping playlist creation")
            return None

        # Skip update if this series hasn't changed and it's not the first creation
        # But ALWAYS create a playlist if one doesn't exist yet
        clean_name = self._clean_filename(base_game)
        m3u_path = self.output_dir / f"{clean_name}.m3u"

        # If the playlist already exists, check if it needs updating
        if m3u_path.exists() and not self._has_series_changed(base_game):
            logger.debug(f"Skipping playlist update for {base_game} - no changes detected")
            return m3u_path

        # If this playlist exists and is user-customized, check for new discs only
        if m3u_path.exists() and clean_name in self.user_customized:
            result = self._update_user_customized_playlist(base_game, m3u_path)
        else:
            # Create or fully update the playlist
            result = self._create_standard_playlist(base_game, m3u_path)

        # Mark as recently updated to prevent redundant updates
        if result:
            self.recently_updated.add(base_game)

        return result

    def _update_user_customized_playlist(self, base_game: str, m3u_path: Path) -> Path:
        """
        Update a user-customized playlist by appending new discs while preserving modifications.

        Args:
            base_game: Base name of the game series
            m3u_path: Path to the M3U file

        Returns:
            Path to the updated M3U file
        """
        logger.info(f"Updating user-customized playlist for {base_game}")

        try:
            # Read existing entries
            existing_entries = self._read_m3u_file(m3u_path)
            existing_files = {Path(entry).name for entry in existing_entries}

            # Identify new entries to add
            new_entries = []
            for chd_path, disc_num in self.game_series[base_game]:
                if chd_path.name not in existing_files:
                    new_entries.append((chd_path, disc_num))

            if not new_entries:
                logger.debug(f"No new discs to add to playlist {m3u_path}")
                return m3u_path

            # Backup existing file
            backup_path = m3u_path.with_suffix(f".m3u.bak")
            import shutil

            shutil.copy2(m3u_path, backup_path)
            logger.debug(f"Created backup of user-customized playlist: {backup_path}")

            # Append new entries to the existing file
            with open(m3u_path, "a", encoding="utf-8") as f:
                f.write("\n# New entries added by 7z-to-CHD Converter\n")
                f.write(f"# Added on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

                for chd_path, disc_num in sorted(new_entries, key=lambda x: x[1]):
                    # Use relative path if file is in the same directory
                    if chd_path.parent == self.output_dir:
                        f.write(f"{chd_path.name}\n")
                    else:
                        f.write(f"{chd_path}\n")

            logger.info(
                f"Updated user-customized playlist {m3u_path} with {len(new_entries)} new discs"
            )
            return m3u_path

        except Exception as e:
            logger.error(f"Failed to update user-customized playlist {m3u_path}: {e}")
            return m3u_path

    def _create_standard_playlist(self, base_game: str, m3u_path: Path) -> Path:
        """
        Create or update a standard M3U playlist managed by this tool.

        Args:
            base_game: Base name of the game series
            m3u_path: Path to the M3U file

        Returns:
            Path to the created M3U file
        """
        is_new = not m3u_path.exists()
        action = "Creating" if is_new else "Updating"
        logger.info(f"{action} playlist for {base_game}")

        try:
            # Create directory if it doesn't exist
            os.makedirs(m3u_path.parent, exist_ok=True)

            # Sort discs by disc number
            sorted_discs = sorted(self.game_series[base_game], key=lambda x: x[1])

            # Get disc information for logging
            disc_nums = [disc_num for _, disc_num in sorted_discs]

            # Verify we have sequential discs
            max_disc = max(disc_nums)
            expected_discs = set(range(1, max_disc + 1))
            actual_discs = set(disc_nums)
            missing_discs = expected_discs - actual_discs

            # Log if we're missing any discs in the sequence
            if missing_discs:
                missing_str = ", ".join(map(str, sorted(missing_discs)))
                logger.warning(
                    f"Creating playlist for {base_game} with missing disc(s): {missing_str}"
                )

            with open(m3u_path, "w", encoding="utf-8") as f:
                # Write header comment with metadata
                f.write(f"# {base_game} - Multi-disc game playlist\n")
                f.write("# Created by 7z-to-CHD Converter\n")
                f.write(f"# Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Total discs: {len(sorted_discs)} ({', '.join(map(str, disc_nums))})\n")
                if missing_discs:
                    f.write(f"# Missing discs: {', '.join(map(str, sorted(missing_discs)))}\n")
                f.write("#\n")

                # Write disc entries
                for chd_path, disc_num in sorted_discs:
                    # Use relative path if file is in the same directory
                    if chd_path.parent == self.output_dir:
                        f.write(f"{chd_path.name} # Disc {disc_num}\n")
                    else:
                        f.write(f"{chd_path} # Disc {disc_num}\n")

            # Mark as created
            clean_name = self._clean_filename(base_game)
            self.created_playlists.add(clean_name)

            # Save state if this is a new playlist
            if is_new:
                self._save_state()

            logger.info(f"{action} playlist {m3u_path} with {len(sorted_discs)} discs")
            return m3u_path

        except Exception as e:
            logger.error(f"Failed to create playlist {m3u_path}: {e}")
            return None

    def scan_directory(
        self, directory: Optional[Union[str, Path]] = None, update_all: bool = False
    ) -> Dict[str, Path]:
        """
        Scan a directory for CHD files and register them as discs.

        Args:
            directory: Directory to scan, defaults to output_dir if not specified
            update_all: Whether to update all playlists or only those for newly found games

        Returns:
            Dictionary mapping base game names to their M3U playlist paths
        """
        scan_dir = Path(directory) if directory else self.output_dir
        if not scan_dir or not scan_dir.exists():
            logger.warning(f"Directory {scan_dir} does not exist, cannot scan")
            return {}

        logger.info(f"Scanning directory {scan_dir} for CHD files")

        # Reset the recently updated set at the start of a full scan
        self.recently_updated = set()

        # Get all CHD files
        chd_files = list(scan_dir.glob("*.chd"))  # Only scan top level, not recursively
        logger.debug(f"Found {len(chd_files)} CHD files")

        # Group CHD files by potential series to avoid processing one at a time
        # This reduces the number of times we update playlists
        series_groups = {}
        for chd_file in chd_files:
            base_game, disc_num = self._extract_base_name_and_disc(chd_file.stem)
            if disc_num:  # Only track multi-disc games
                if base_game not in series_groups:
                    series_groups[base_game] = []
                series_groups[base_game].append((chd_file, disc_num))

        # Process each series
        for base_game, discs in series_groups.items():
            # Reset the series signature to force a fresh comparison
            if base_game in self.series_signatures:
                del self.series_signatures[base_game]

            for chd_file, disc_num in discs:
                self._add_to_game_series(base_game, chd_file, disc_num)

        # Create playlists for all series with multiple discs
        created_playlists = {}

        # Only create/update playlists for complete series
        for base_game, disc_list in self.game_series.items():
            if len(disc_list) > 1:
                # Check if we have a complete series
                disc_numbers = [d for _, d in disc_list]
                max_disc = max(disc_numbers)
                is_complete = all(i in disc_numbers for i in range(1, max_disc + 1))

                # Only update if we have all discs or if update_all is requested
                if update_all or is_complete:
                    m3u_path = self.update_playlist(base_game)
                    if m3u_path:
                        created_playlists[base_game] = m3u_path

        # Save state
        self._save_state()

        # Only log created count if we actually created/updated any
        if created_playlists:
            logger.info(f"Created/updated {len(created_playlists)} playlists")
        return created_playlists

    def check_for_incomplete_series(
        self, min_discs: int = 2, expected_max_discs: int = 6, force_scan: bool = False
    ) -> Dict[str, Path]:
        """
        Check for incomplete game series and create playlists for them.

        Args:
            min_discs: Minimum number of discs required to create a playlist
            expected_max_discs: Expected maximum number of discs in a complete series
            force_scan: Whether to force a complete directory scan (otherwise uses cached data)

        Returns:
            Dictionary mapping base game names to their playlist paths
        """
        if not self.output_dir or not self.output_dir.exists():
            logger.warning("Output directory not set or doesn't exist")
            return {}

        # Only log this message for a full scan
        if force_scan:
            logger.info(f"Checking for incomplete game series (min discs: {min_discs})")
            # Refresh the game series data by scanning for CHD files
            self.scan_directory(self.output_dir)
        else:
            logger.debug(f"Checking existing tracked series for playlist creation")

        # Create playlists for series with at least min_discs but potentially incomplete
        created_playlists = {}
        for base_game, disc_list in self.game_series.items():
            # Check if we need to look for additional discs
            if force_scan or len(disc_list) == min_discs:
                self._find_related_discs(base_game)

            # Only process if we have enough discs
            if len(disc_list) >= min_discs:
                # Check if we have reasonable disc sequence
                disc_nums = sorted([disc_num for _, disc_num in disc_list])

                # Check if the highest disc number is reasonable
                max_disc = max(disc_nums)
                if max_disc <= expected_max_discs:
                    # Check if we have the first disc or starting with a low number
                    if 1 in disc_nums or min(disc_nums) < 3:
                        # Check if we have sequential discs starting from 1
                        has_consecutive = True
                        for i in range(1, max_disc):
                            if i not in disc_nums and i + 1 in disc_nums:
                                has_consecutive = False
                                break

                        if has_consecutive:
                            m3u_path = self.update_playlist(base_game)
                            if m3u_path:
                                created_playlists[base_game] = m3u_path
                                # Only log if we actually created a new playlist
                                clean_name = self._clean_filename(base_game)
                                if clean_name not in self.created_playlists:
                                    logger.info(
                                        f"Created playlist for game series: {base_game} (discs: {disc_nums})"
                                    )

        # Save state
        if created_playlists:
            self._save_state()

        return created_playlists

    def get_series_status(self) -> Dict[str, Dict]:
        """
        Get the status of all tracked game series.

        Returns:
            Dictionary with status information for each game series
        """
        status = {}

        for base_game, disc_list in self.game_series.items():
            disc_nums = sorted([disc_num for _, disc_num in disc_list])
            clean_name = self._clean_filename(base_game)

            # Check if this series has a playlist
            has_playlist = clean_name in self.created_playlists

            # Check if the playlist is user-customized
            is_customized = clean_name in self.user_customized

            # Calculate completeness status
            missing_discs = []
            if disc_nums:
                max_disc = max(disc_nums)
                for i in range(1, max_disc + 1):
                    if i not in disc_nums:
                        missing_discs.append(i)

            status[base_game] = {
                "disc_count": len(disc_list),
                "disc_numbers": disc_nums,
                "has_playlist": has_playlist,
                "is_customized": is_customized,
                "missing_discs": missing_discs,
                "is_complete": not missing_discs and disc_nums and 1 in disc_nums,
            }

        return status

    def cleanup(self) -> None:
        """
        Save state and clean up resources.
        """
        # Save state before cleanup
        self._save_state()

        # Clear the recently updated set
        self.recently_updated = set()

        logger.debug("PlaylistManager cleanup complete")


# Example usage in main script:
if __name__ == "__main__":
    # Set up logging for testing
    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    import argparse

    parser = argparse.ArgumentParser(
        description="Create and manage M3U playlists for multi-disc games"
    )
    parser.add_argument("directory", help="Directory containing CHD files")
    parser.add_argument("--state-file", "-s", help="Path to state file for persistence")
    parser.add_argument(
        "--check-incomplete",
        "-c",
        action="store_true",
        help="Check for incomplete series and create playlists if possible",
    )

    args = parser.parse_args()

    directory = Path(args.directory)

    # Create playlist manager
    manager = PlaylistManager(output_dir=directory, state_file=args.state_file)

    # Scan directory and create playlists
    created = manager.scan_directory()

    print(f"Created/updated {len(created)} playlists")

    # Check for incomplete series if requested
    if args.check_incomplete:
        incomplete = manager.check_for_incomplete_series()
        print(f"Created {len(incomplete)} playlists for incomplete series")

    # Print status of game series
    status = manager.get_series_status()
    for game, info in status.items():
        completeness = "Complete" if info["is_complete"] else "Incomplete"
        print(f"{game}: {info['disc_count']} discs - {completeness}")
        if info["missing_discs"]:
            print(f"  Missing discs: {info['missing_discs']}")
