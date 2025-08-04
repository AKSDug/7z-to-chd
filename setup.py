#!/usr/bin/env python3
"""
7z-to-CHD Converter - Setup Script
Cross-platform utility for extraction of .7z archives and conversion to CHD format

Author: AKSDug
Repository: https://github.com/AKSDug/7z-to-chd
"""

import os
import sys
import platform
import subprocess
import shutil
import logging
from pathlib import Path

# Import version info
try:
    from __version__ import __version__
except ImportError:
    __version__ = "1.0.2"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("setup")

# Global variables
SCRIPT_DIR = Path(__file__).parent.absolute()
TOOLS_DIR = SCRIPT_DIR / "tools"
CHDMAN_DIR = TOOLS_DIR / "chdman"
LIB_DIR = SCRIPT_DIR / "lib"
LOGS_DIR = SCRIPT_DIR / "logs"


def setup_directories():
    """Create necessary directories if they don't exist."""
    for directory in [TOOLS_DIR, CHDMAN_DIR, LIB_DIR, LOGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Directory ready: {directory}")


def get_system_info():
    """Detect operating system and architecture."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    # Normalize architecture names
    arch_map = {
        "x86_64": "x64",
        "amd64": "x64",
        "i386": "x86",
        "i686": "x86",
        "armv7l": "arm",
        "armv8l": "arm64",
        "aarch64": "arm64",
    }

    arch = arch_map.get(machine, machine)
    logger.info(f"Detected system: {system} {arch}")
    return system, arch


def install_python_dependencies():
    """Install required Python packages."""
    logger.info("Installing Python dependencies...")
    requirements = ["py7zr", "tqdm", "colorama", "psutil"]

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", *requirements])

        # Create requirements.txt
        with open(SCRIPT_DIR / "requirements.txt", "w") as f:
            f.write("\n".join(requirements))

        logger.info("Python dependencies installed successfully.")
    except Exception as e:
        logger.error(f"Failed to install Python dependencies: {e}")
        sys.exit(1)


def prompt_for_chdman_path(system):
    """
    Prompt the user to specify the path to chdman.

    Args:
        system (str): The operating system ('windows', 'darwin', 'linux')

    Returns:
        Path or None: Path to chdman if provided and valid, None otherwise
    """
    chdman_exec_name = "chdman.exe" if system == "windows" else "chdman"

    print("\n" + "=" * 60)
    print("Please enter the path to the chdman executable or its directory.")
    print("chdman is required for CHD conversion and is typically included with MAME.")
    print("Common locations include:")
    print(" - Windows: C:\\Program Files\\MAME or C:\\path\\to\\emulator\\MAME")
    print(" - macOS: /Applications/MAME.app/Contents/MacOS")
    print(" - Linux: /usr/bin or /usr/local/bin")
    print("=" * 60)

    user_path = input("> ").strip()

    if not user_path:
        logger.warning("No path provided")
        return None

    # Convert to Path object
    chdman_path = Path(user_path)

    # Check if the path is a directory, and if so, append the executable name
    if chdman_path.is_dir():
        chdman_path = chdman_path / chdman_exec_name

    # Verify the path
    if chdman_path.exists():
        if chdman_path.is_file():
            if system != "windows" and not os.access(chdman_path, os.X_OK):
                logger.warning(f"File found but not executable: {chdman_path}")
                try:
                    os.chmod(chdman_path, 0o755)
                    logger.info(f"Made executable: {chdman_path}")
                except Exception as e:
                    logger.error(f"Could not make executable: {e}")
                    return None
            logger.info(f"Valid chdman path: {chdman_path}")
            return chdman_path
        else:
            logger.warning(f"Path exists but is not a file: {chdman_path}")
    else:
        logger.warning(f"Path does not exist: {chdman_path}")

    return None


def setup_chdman():
    """Set up chdman tool."""
    logger.info("Setting up chdman...")

    system, _ = get_system_info()
    config_file = SCRIPT_DIR / "chdman_path.txt"

    # Check if chdman is already configured
    if config_file.exists():
        with open(config_file, "r") as f:
            chdman_path = f.read().strip()
            if os.path.exists(chdman_path):
                logger.info(f"Using previously configured chdman at: {chdman_path}")
                return True

    # Check if chdman is in PATH
    chdman_in_path = shutil.which("chdman")
    if chdman_in_path:
        logger.info(f"Found chdman in PATH: {chdman_in_path}")
        # Store the path rather than copying
        with open(config_file, "w") as f:
            f.write(chdman_in_path)
        return True

    # Prompt the user for the path to chdman
    chdman_path = prompt_for_chdman_path(system)
    if chdman_path:
        # Store the path in a configuration file
        config_file = SCRIPT_DIR / "chdman_path.txt"
        with open(config_file, "w") as f:
            f.write(str(chdman_path))
        logger.info(f"chdman path stored in configuration file: {config_file}")
        return True

    logger.warning("Could not set up chdman.")
    logger.warning("You will be prompted for the chdman path when running the conversion.")
    return False


def main():
    """Main setup function."""
    logger.info(f"Starting 7z-to-CHD Converter v{__version__} setup...")

    try:
        # Create directories
        setup_directories()

        # Install Python dependencies
        install_python_dependencies()

        # Setup chdman
        chdman_setup_success = setup_chdman()

        if chdman_setup_success:
            logger.info("Setup completed successfully!")
        else:
            logger.warning("Setup completed with warnings!")
            logger.warning(
                "chdman was not found or configured. You'll need to provide its path during conversion."
            )

        logger.info("You can now run 'convert.py' to start the conversion process.")

    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
