#!/usr/bin/env python3
import os
import sys
import re
import subprocess
import tempfile
import platform
from pathlib import Path
from collections import defaultdict

def check_dependencies():
    """Check for required dependencies and return the path to CHDMan"""
    try:
        import py7zr
        print("py7zr package is available.")
    except ImportError:
        print("Required package 'py7zr' is not installed.")
        print("Running pip to install dependencies...")
        try:
            print(f"Running: {sys.executable} -m pip install py7zr")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "py7zr"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            if result.returncode != 0:
                print(f"Installation failed with error: {result.stderr}")
                print("Please install py7zr manually with: pip install py7zr")
                sys.exit(1)
            else:
                print("Successfully installed py7zr.")
                # Re-import to ensure it's available
                import py7zr
        except Exception as e:
            print(f"Failed to install dependencies: {e}")
            print("Please run 'pip install py7zr' manually.")
            sys.exit(1)
    
    # Create tools directory
    tools_dir = Path("./tools").absolute()
    tools_dir.mkdir(exist_ok=True)
    print(f"Using tools directory: {tools_dir}")
    
    # Setup CHDMan wrapper script based on platform
    system = platform.system()
    print(f"Detected operating system: {system}")
    
    # Determine script path
    if system == "Windows":
        wrapper_script = tools_dir / "run_chdman.bat"
    else:
        wrapper_script = tools_dir / "run_chdman.sh"
    
    # Check if script exists, if not create it
    if not wrapper_script.exists():
        print(f"CHDMan wrapper script not found. Creating at: {wrapper_script}")
        try:
            # Try to import from local setup.py
            try:
                from setup import setup_chdman
                setup_chdman()
            except ImportError:
                # If local import fails, define and run setup_chdman here
                print("Local setup.py not found, creating CHDMan wrapper directly.")
                
                if system == "Windows":
                    # Create Windows batch script
                    with open(wrapper_script, 'w', encoding='utf-8') as f:
                        f.write('@echo off\n')
                        f.write('set SCRIPT_DIR=%~dp0\n')
                        f.write('if exist "%SCRIPT_DIR%chdman.exe" (\n')
                        f.write('    "%SCRIPT_DIR%chdman.exe" %*\n')
                        f.write('    exit /b %ERRORLEVEL%\n')
                        f.write(') else (\n')
                        f.write('    where chdman >nul 2>nul\n')
                        f.write('    if %ERRORLEVEL% == 0 (\n')
                        f.write('        chdman %*\n')
                        f.write('        exit /b %ERRORLEVEL%\n')
                        f.write('    ) else (\n')
                        f.write('        echo CHDMan not found. Attempting download...\n')
                        f.write('        powershell -Command "& {try { $url = \'https://github.com/mamedev/mame/raw/master/chdman.exe\'; $output = \'%SCRIPT_DIR%chdman.exe\'; (New-Object System.Net.WebClient).DownloadFile($url, $output); Write-Host \'Download successful\' } catch { Write-Host $_.Exception.Message }}"\n')
                        f.write('        if exist "%SCRIPT_DIR%chdman.exe" (\n')
                        f.write('            echo CHDMan downloaded successfully.\n')
                        f.write('            "%SCRIPT_DIR%chdman.exe" %*\n')
                        f.write('            exit /b %ERRORLEVEL%\n')
                        f.write('        ) else (\n')
                        f.write('            echo Failed to download CHDMan.\n')
                        f.write('            echo Please download chdman.exe manually from https://github.com/mamedev/mame/raw/master/chdman.exe\n')
                        f.write('            echo and place it in the tools directory.\n')
                        f.write('            exit /b 1\n')
                        f.write('        )\n')
                        f.write('    )\n')
                        f.write(')\n')
                else:
                    # Create Unix shell script
                    with open(wrapper_script, 'w', encoding='utf-8') as f:
                        f.write('#!/bin/bash\n\n')
                        f.write('# Exit on error, display commands\n')
                        f.write('set -e\n\n')
                        f.write('SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n')
                        f.write('echo "Looking for CHDMan in $SCRIPT_DIR/chdman"\n\n')
                        
                        f.write('if [ -f "$SCRIPT_DIR/chdman" ]; then\n')
                        f.write('    echo "Using CHDMan from tools directory"\n')
                        f.write('    chmod +x "$SCRIPT_DIR/chdman"\n')
                        f.write('    "$SCRIPT_DIR/chdman" "$@"\n')
                        f.write('    exit $?\n')
                        f.write('elif command -v chdman >/dev/null 2>&1; then\n')
                        f.write('    echo "Using system-installed CHDMan"\n')
                        f.write('    chdman "$@"\n')
                        f.write('    exit $?\n')
                        f.write('else\n')
                        f.write('    echo "CHDMan not found. Downloading..."\n')
                        f.write('    # Try direct binary download first\n')
                        f.write('    if curl -L -o "$SCRIPT_DIR/chdman" "https://github.com/mamedev/mame/raw/master/chdman" 2>/dev/null; then\n')
                        f.write('        echo "Downloaded CHDMan binary directly"\n')
                        f.write('        chmod +x "$SCRIPT_DIR/chdman"\n')
                        f.write('        "$SCRIPT_DIR/chdman" "$@"\n')
                        f.write('        exit $?\n')
                        f.write('    else\n')
                        f.write('        echo "Direct download failed, trying package managers..."\n')
                        f.write('        if [ "$(uname)" == "Darwin" ]; then\n')
                        f.write('            # macOS\n')
                        f.write('            if command -v brew >/dev/null 2>&1; then\n')
                        f.write('                echo "Installing via Homebrew..."\n')
                        f.write('                brew install mame-tools || echo "Homebrew installation failed"\n')
                        f.write('            fi\n')
                        f.write('        else\n')
                        f.write('            # Linux\n')
                        f.write('            if command -v apt-get >/dev/null 2>&1; then\n')
                        f.write('                echo "Installing via apt..."\n')
                        f.write('                sudo apt-get update && sudo apt-get install -y mame-tools || echo "APT installation failed"\n')
                        f.write('            elif command -v dnf >/dev/null 2>&1; then\n')
                        f.write('                echo "Installing via dnf..."\n')
                        f.write('                sudo dnf install -y mame-tools || echo "DNF installation failed"\n')
                        f.write('            elif command -v pacman >/dev/null 2>&1; then\n')
                        f.write('                echo "Installing via pacman..."\n')
                        f.write('                sudo pacman -S --noconfirm mame-tools || echo "Pacman installation failed"\n')
                        f.write('            fi\n')
                        f.write('        fi\n\n')
                        
                        f.write('        # Check if installation succeeded\n')
                        f.write('        if command -v chdman >/dev/null 2>&1; then\n')
                        f.write('            echo "CHDMan installed successfully via package manager"\n')
                        f.write('            chdman "$@"\n')
                        f.write('            exit $?\n')
                        f.write('        else\n')
                        f.write('            echo "CHDMan installation failed."\n')
                        f.write('            echo "Please install CHDMan manually and retry."\n')
                        f.write('            exit 1\n')
                        f.write('        fi\n')
                        f.write('    fi\n')
                        f.write('fi\n')
                    
                    # Make the script executable
                    os.chmod(wrapper_script, 0o755)
        
        except Exception as e:
            print(f"Error creating CHDMan wrapper script: {e}")
            sys.exit(1)
    
    # Try to download CHDMan directly if not present
    if system == "Windows":
        chdman_path = tools_dir / "chdman.exe"
        chdman_url = "https://github.com/mamedev/mame/raw/master/chdman.exe"
    else:
        chdman_path = tools_dir / "chdman"
        chdman_url = "https://github.com/mamedev/mame/raw/master/chdman"
    
    if not chdman_path.exists():
        print(f"CHDMan binary not found at {chdman_path}. Attempting direct download...")
        try:
            import urllib.request
            urllib.request.urlretrieve(chdman_url, str(chdman_path))
            
            if not system == "Windows":
                os.chmod(chdman_path, 0o755)  # Make executable on Unix
                
            print(f"CHDMan binary downloaded to: {chdman_path}")
        except Exception as e:
            print(f"Direct download failed: {e}")
            print("CHDMan will be downloaded when needed via the wrapper script.")
    
    print(f"Using CHDMan wrapper: {wrapper_script}")
    return str(wrapper_script)

def extract_7z(archive_path, extract_path):
    """Extract a .7z archive to the specified path"""
    print(f"Extracting {archive_path}...")
    try:
        import py7zr
        with py7zr.SevenZipFile(archive_path, mode='r') as z:
            z.extractall(path=extract_path)
        print("Extraction completed.")
        return True
    except Exception as e:
        print(f"Error extracting {archive_path}: {e}")
        return False

def find_disk_image(extract_path):
    """Find disk image files in the extracted directory"""
    image_extensions = ['.iso', '.bin', '.img', '.gdi', '.cue']
    for root, _, files in os.walk(extract_path):
        for file in files:
            if any(file.lower().endswith(ext) for ext in image_extensions):
                return os.path.join(root, file)
    return None

def convert_to_chd(disk_image, output_path, chdman_script):
    """Convert disk image to CHD format using CHDMan"""
    disk_name = os.path.splitext(os.path.basename(disk_image))[0]
    output_chd = os.path.join(output_path, f"{disk_name}.chd")
    
    print(f"Converting {disk_image} to CHD...")
    print(f"Using CHDMan script at: {chdman_script}")
    
    # Ensure disk_image path is absolute
    disk_image = os.path.abspath(disk_image)
    output_chd = os.path.abspath(output_chd)
    
    if not os.path.exists(disk_image):
        print(f"ERROR: Source disk image not found: {disk_image}")
        return None
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_chd), exist_ok=True)
    
    # Use appropriate command based on platform
    if platform.system() == "Windows":
        base_command = [chdman_script]
    else:
        base_command = ["bash", chdman_script]
    
    # Add chdman-specific parameters
    command = base_command + ["createcd", "-i", disk_image, "-o", output_chd]
    
    print(f"Executing command: {' '.join(command)}")
    
    try:
        # Run with output capture for better debugging
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            print(f"CHDMan execution failed with return code: {process.returncode}")
            print(f"Standard output: {stdout}")
            print(f"Error output: {stderr}")
            return None
        
        if os.path.exists(output_chd):
            print(f"Conversion to CHD successful: {output_chd}")
            return output_chd
        else:
            print(f"CHDMan command appeared to succeed, but output file was not created: {output_chd}")
            print(f"Standard output: {stdout}")
            print(f"Error output: {stderr}")
            return None
            
    except Exception as e:
        print(f"Error executing CHDMan: {e}")
        return None

def create_m3u(game_name, chd_files, output_path):
    """Create an .m3u file for multi-disk games"""
    if not chd_files:
        print(f"No CHD files to create M3U for: {game_name}")
        return None
    
    # Clean up game name for filename
    safe_game_name = re.sub(r'[<>:"/\\|?*]', '_', game_name)
    m3u_path = os.path.join(output_path, f"{safe_game_name}.m3u")
    
    with open(m3u_path, 'w', encoding='utf-8') as f:
        for chd_file in chd_files:
            f.write(f"{os.path.basename(chd_file)}\n")
    
    print(f"Created M3U file: {m3u_path}")
    return m3u_path

def group_by_game(archive_paths):
    """Group archives by game name to handle multi-disk sets"""
    game_groups = defaultdict(list)
    
    # Common multi-disk naming patterns
    patterns = [
        r'^(.+?)[\s_-]*disc[\s_-]*(\d+)',  # Matches "Game Name Disc 1"
        r'^(.+?)[\s_-]*disk[\s_-]*(\d+)',  # Matches "Game Name Disk 1"
        r'^(.+?)[\s_-]*cd[\s_-]*(\d+)',    # Matches "Game Name CD 1"
        r'^(.+?)\s*\(Disc\s*(\d+)\)',      # Matches "Game Name (Disc 1)"
        r'^(.+?)\s*\(Disk\s*(\d+)\)',      # Matches "Game Name (Disk 1)"
        r'^(.+?)\s*\(CD\s*(\d+)\)'         # Matches "Game Name (CD 1)"
    ]
    
    # Extract disk number for sorting
    def get_disk_number(path):
        filename = os.path.splitext(os.path.basename(path))[0]
        for pattern in patterns:
            match = re.match(pattern, filename, re.IGNORECASE)
            if match:
                return int(match.group(2))
        return 0  # Default for files without a disk number
    
    # Sort archive paths to ensure consistent ordering
    sorted_archives = sorted(archive_paths, key=lambda x: (os.path.splitext(os.path.basename(x))[0], get_disk_number(x)))
    
    for archive_path in sorted_archives:
        file_name = os.path.splitext(os.path.basename(archive_path))[0]
        matched = False
        
        for pattern in patterns:
            match = re.match(pattern, file_name, re.IGNORECASE)
            if match:
                game_name = match.group(1).strip()
                disk_number = int(match.group(2))
                # Store as a tuple with disk number for proper ordering
                game_groups[game_name].append((disk_number, archive_path))
                matched = True
                break
        
        if not matched:
            # If no pattern matches, treat as a single-disk game
            game_groups[file_name].append((1, archive_path))
    
    # Sort each game's disks by disk number and extract just the paths
    result = {}
    for game, disks in game_groups.items():
        result[game] = [path for _, path in sorted(disks)]
    
    return result

def process_archives(input_dir, output_dir, keep_original, chdman_script):
    """Process all .7z archives in the input directory"""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all .7z files
    archive_paths = []
    for file in os.listdir(input_dir):
        if file.lower().endswith('.7z'):
            archive_paths.append(os.path.join(input_dir, file))
    
    if not archive_paths:
        print(f"No .7z files found in {input_dir}")
        return
    
    print(f"Found {len(archive_paths)} .7z archives")
    
    # Group archives by game
    game_groups = group_by_game(archive_paths)
    print(f"Identified {len(game_groups)} games/game sets")
    
    for game_name, archives in game_groups.items():
        print(f"\nProcessing game: {game_name}")
        chd_files = []
        
        for archive_path in archives:
            print(f"Processing archive: {os.path.basename(archive_path)}")
            
            # Create a temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract the .7z archive
                if not extract_7z(archive_path, temp_dir):
                    continue
                
                # Find the disk image
                disk_image = find_disk_image(temp_dir)
                if not disk_image:
                    print(f"No supported disk image found in {archive_path}")
                    continue
                
                # Convert to CHD
                chd_file = convert_to_chd(disk_image, output_dir, chdman_script)
                if chd_file:
                    chd_files.append(chd_file)
                
                # Delete original archive if specified
                if not keep_original and chd_file:  # Only delete if conversion was successful
                    print(f"Deleting original archive: {archive_path}")
                    try:
                        os.remove(archive_path)
                    except Exception as e:
                        print(f"Error deleting {archive_path}: {e}")
        
        # Create .m3u file for multi-disk games
        if len(chd_files) > 1:
            create_m3u(game_name, chd_files, output_dir)

def main():
    print("===== 7z to CHD Conversion Tool =====")
    
    # Check dependencies and get chdman path
    chdman_script = check_dependencies()
    
    # Get user input
    input_dir = input("Enter path to folder containing .7z files: ").strip()
    if not os.path.isdir(input_dir):
        print(f"Error: {input_dir} is not a valid directory")
        return
    
    output_dir = input("Enter path for output CHD and .m3u files: ").strip()
    
    while True:
        keep_option = input("Keep original files? Enter 'keep' or 'delete': ").strip().lower()
        if keep_option in ['keep', 'delete']:
            break
        print("Invalid option. Please enter 'keep' or 'delete'.")
    
    keep_original = (keep_option == 'keep')
    
    # Process archives
    process_archives(input_dir, output_dir, keep_original, chdman_script)
    
    print("\nConversion process completed!")

if __name__ == "__main__":
    main()