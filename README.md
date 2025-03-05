# 7z-to-CHD Converter

Version 1.0.1

A cross-platform utility for bulk extraction of .7z archives and conversion to CHD format, with automatic handling for multi-disk games.

This tool was created out of frustration with existing conversion utilities that either imposed overly strict requirements or lacked efficient batch processing capabilities. Our goal was to develop a powerful yet simple solution that eliminates common pain points in the ROM conversion workflow.

## Overview

7z-to-CHD Converter handles the complex process of extracting and converting disk images while presenting a straightforward interface to the user. Although primarily tested with Dreamcast games, the tool follows best practices for maximum compatibility and should work seamlessly with other console formats that support CHD conversion.

## Features

- Extracts files from .7z archives with smart resource management
- Converts disc image formats (ISO, BIN/CUE, GDI, NRG, etc.) to CHD
- Creates .m3u playlists for multi-disk games automatically
- Implements efficient resume functionality to avoid redundant processing
- Cross-platform (Windows, macOS, Linux)
- Multithreading support with adaptive resource allocation
- Detailed logging for troubleshooting

## Repository Structure

```
7z-to-chd/
├── README.md
├── setup.py          # Sets up dependencies and tools
├── convert.py        # Main conversion script
├── requirements.txt  # Python dependencies
└── lib/              # Core functionality modules
    ├── __init__.py
    ├── extractor.py  # 7z extraction handling
    ├── converter.py  # CHD conversion
    ├── playlist.py   # Multi-disk game detection/playlist creation
    └── utils.py      # Common utility functions
```

## Requirements

- Python 3.7 or higher
- chdman utility (part of the MAME distribution)
- Internet connection (for initial setup)

## Installation

Run the setup script to install all dependencies:

```bash
# Windows
python setup.py

# macOS/Linux
python3 setup.py
```

The setup script will:
1. Install required Python packages (py7zr, tqdm, colorama, psutil)
2. Attempt to locate or set up the chdman tool in the following order:
   - Check if chdman is already installed in the tools directory
   - Check if chdman is available in the system PATH
   - Search common installation locations for MAME and chdman
   - Prompt you to provide the path to chdman if not found automatically

### About chdman

The chdman utility is a tool distributed with MAME (Multiple Arcade Machine Emulator) that handles CHD (Compressed Hunks of Data) files. If you already have MAME installed, the setup script will attempt to find chdman automatically.

If chdman isn't found automatically, you'll be prompted to provide its location. Common locations include:

- Windows: `C:\Program Files\MAME\chdman.exe`
- macOS: `/Applications/MAME.app/Contents/MacOS/chdman`
- Linux: `/usr/bin/chdman` or `/usr/local/bin/chdman`

You can download MAME from the [official MAME website](https://www.mamedev.org/release.html) or the [MAME GitHub repository](https://github.com/mamedev/mame/releases).

**Important:** The tool will use chdman directly from its installation location rather than making a copy. This prevents permission issues and ensures you're always using the correct version.

## Usage

Run the conversion script:

```bash
# Windows
python convert.py

# macOS/Linux
python3 convert.py
```

The script will prompt you for:
1. Source directory (containing .7z files)
2. Destination directory (for CHD and .m3u files)
3. Whether to keep or delete original files
4. Multithreading limitations

If chdman wasn't found during setup, you'll be prompted to provide its path the first time you run a conversion.

### Command-line Arguments

You can also specify arguments directly:

```bash
python convert.py --source "/path/to/7z/files" --destination "/path/to/output" --keep yes --threads 4
```

Available options:
- `--source`, `-s`: Source directory containing .7z files
- `--destination`, `-d`: Destination directory for CHD and .m3u files
- `--keep`, `-k`: Keep original files after conversion (yes/no)
- `--threads`, `-t`: Maximum number of concurrent operations (0 for CPU count)
- `--verbose`, `-v`: Enable verbose logging

## Logging

Detailed logs are stored in the `logs` directory. Each run creates a timestamped log file for troubleshooting purposes.

## Troubleshooting

If you encounter issues:

1. Check the logs in the `logs` directory
2. Ensure all dependencies were correctly installed
3. Verify that source files are valid .7z archives
4. Make sure chdman is properly installed and configured:
   - If you get errors about chdman not being found, run the setup script again or manually provide the path when prompted
   - If you know where chdman is installed, you can create a file named `chdman_path.txt` in the project root containing the full path to chdman

### Common Issues

- **Error Code 3221225786**: This is a Windows-specific error often related to memory issues or file access problems. Try:
  - Using a smaller number of worker threads (e.g., 2 instead of 4)
  - Ensuring you have sufficient disk space
  - Running the script with administrator privileges
  
- **"nan% complete" messages**: These may appear during conversion but usually don't indicate a problem unless the conversion fails. This is a display issue from chdman.

- **Individual track files**: The tool might create multiple small CHD files for multi-track games. This is unlikely with .cue files used for proper multi-track handling.

## Compatibility

While primarily tested with Dreamcast games, this tool should work with disc images from any console system that chdman supports, including:

- PlayStation/PS2
- Sega CD/Saturn/Dreamcast
- PC Engine CD/TurboGrafx-CD
- 3DO
- PC-FX
- Neo Geo CD
- Other CD-based systems

The tool detects and handles various disc image formats including ISO, BIN/CUE, GDI, NRG, CDI, and more.

## Version History

- 1.0.1 - Fixed playlist generation for games with more than two discs
- 1.0.0 - Initial release

## Acknowledgments

This project uses or references code and concepts from the following open-source projects:

- [MAME Project](https://github.com/mamedev/mame) - For the chdman utility that provides CHD compression functionality
- [py7zr](https://github.com/miurahr/py7zr) - Python library for 7z archive handling
- [tqdm](https://github.com/tqdm/tqdm) - For progress bar functionality
- [colorama](https://github.com/tartley/colorama) - For cross-platform colored terminal output
- [psutil](https://github.com/giampaolo/psutil) - For system resource monitoring

## License

MIT

## Author

Created by AKSDug