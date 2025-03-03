# 7z to CHD Conversion Tool

A cross-platform utility for batch converting .7z archives containing disk images to CHD format, with special handling for multi-disk games.

## Features

- **Batch processing** of .7z archives to CHD format
- **Multi-disk game support** with automatic .m3u playlist creation
- **Cross-platform compatibility** (Windows, Linux, macOS)
- **Self-contained operation** with automatic dependency installation
- **Flexible disk image support** (ISO, BIN/CUE, GDI, IMG, etc.)
- **Smart game detection** to properly group related disks
- **Original file management** with options to keep or delete source files

## Requirements

- Python 3.6 or higher
- Internet connection (for initial dependency installation)

The script will automatically install all other required dependencies:
- py7zr (for .7z extraction)
- CHDMan (downloaded automatically if needed)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/AKSDug/7z-to-chd.git
   cd 7z-to-chd
   ```

2. Ensure Python 3.6+ is installed on your system

## Usage

1. Run the main script:
   ```
   python 7z_to_chd.py
   ```

2. Follow the prompts:
   - Enter path to folder containing .7z files
   - Enter path for output CHD and .m3u files
   - Choose whether to keep or delete original .7z files

## How It Works

1. The script scans the specified directory for .7z archives
2. It groups files that appear to be part of multi-disk sets
3. Each archive is extracted to a temporary directory
4. Disk images are located within the extracted content
5. CHDMan is used to convert the disk images to CHD format
6. For multi-disk games, .m3u playlists are created
7. Original .7z archives are kept or deleted based on user preference

## File Naming Conventions

The script can recognize various naming patterns for multi-disk games:

- Game Name Disc 1.7z, Game Name Disc 2.7z
- Game Name Disk 1.7z, Game Name Disk 2.7z
- Game Name CD 1.7z, Game Name CD 2.7z
- Game Name (Disc 1).7z, Game Name (Disc 2).7z
- Game Name (Disk 1).7z, Game Name (Disk 2).7z
- Game Name (CD 1).7z, Game Name (CD 2).7z

## Support and Contributions

Issues and pull requests are welcome! Please feel free to contribute to this project.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
