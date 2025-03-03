#!/usr/bin/env python3
import os
import sys
import platform
import subprocess
import urllib.request
from pathlib import Path

def check_pip_dependencies():
    """Check and install required Python dependencies"""
    try:
        import py7zr
        print("py7zr is already installed.")
    except ImportError:
        print("Installing required package: py7zr")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "py7zr"])
        print("Successfully installed py7zr.")

def setup_chdman():
    """Set up CHDMan tool"""
    tools_dir = Path("./tools")
    tools_dir.mkdir(exist_ok=True)
    
    system = platform.system()
    
    # Create wrapper scripts to find and use chdman
    if system == "Windows":
        # Windows batch script for direct CHDMan execution
        batch_path = tools_dir / "run_chdman.bat"
        
        # Download CHDMan directly
        chdman_exe_path = tools_dir / "chdman.exe"
        if not chdman_exe_path.exists():
            print("CHDMan not found. Downloading from MAME repository...")
            try:
                # Direct download URL for chdman.exe
                chdman_url = "https://github.com/mamedev/mame/raw/master/chdman.exe"
                print(f"Downloading from: {chdman_url}")
                
                import urllib.request
                urllib.request.urlretrieve(chdman_url, str(chdman_exe_path))
                
                if chdman_exe_path.exists():
                    print(f"Successfully downloaded CHDMan to: {chdman_exe_path}")
                else:
                    print("Download completed but file not found - this is unexpected")
            except Exception as e:
                print(f"Error downloading CHDMan: {e}")
                print("Will create a script to attempt download at runtime")
        
        # Create the batch script
        with open(batch_path, 'w', encoding='utf-8') as f:
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
            f.write('        echo Direct download from: https://github.com/mamedev/mame/raw/master/chdman.exe\n')
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
        print(f"Created Windows wrapper script: {batch_path}")
    else:
        # Unix shell script with improved error handling
        shell_path = tools_dir / "run_chdman.sh"
        chdman_bin_path = tools_dir / "chdman"
        
        # Try to download chdman binary directly if it doesn't exist
        if not chdman_bin_path.exists():
            print("CHDMan not found. Trying to download the Linux binary...")
            try:
                chdman_url = "https://github.com/mamedev/mame/raw/master/chdman"
                print(f"Downloading from: {chdman_url}")
                
                import urllib.request
                urllib.request.urlretrieve(chdman_url, str(chdman_bin_path))
                os.chmod(chdman_bin_path, 0o755)  # Make executable
                
                if chdman_bin_path.exists():
                    print(f"Successfully downloaded CHDMan to: {chdman_bin_path}")
                else:
                    print("Download completed but file not found - this is unexpected")
            except Exception as e:
                print(f"Error downloading CHDMan: {e}")
                print("Will create a script to attempt to install at runtime")
        
        # Create a more robust shell script
        with open(shell_path, 'w', encoding='utf-8') as f:
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
            f.write('            else\n')
            f.write('                echo "Homebrew not found."\n')
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
            f.write('            else\n')
            f.write('                echo "No supported package manager found."\n')
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
        
        os.chmod(shell_path, 0o755)  # Make the script executable
        print(f"Created Unix wrapper script: {shell_path}")

    # Test if chdman is available
    wrapper = str(batch_path if system == "Windows" else shell_path)
    try:
        if system == "Windows":
            subprocess.run([wrapper, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            subprocess.run(["sh", wrapper, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("CHDMan is available and working.")
    except Exception:
        print("Note: CHDMan will be downloaded when you run the conversion script.")

def main():
    print("===== 7z to CHD Conversion Tool Setup =====")
    
    # Check and install pip dependencies
    check_pip_dependencies()
    
    # Set up CHDMan
    setup_chdman()
    
    print("\nSetup complete! You can now run the 7z_to_chd.py script to convert your files.")

if __name__ == "__main__":
    main()