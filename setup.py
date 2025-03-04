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
import urllib.request
import zipfile
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('setup')

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
        'x86_64': 'x64', 'amd64': 'x64', 'i386': 'x86', 'i686': 'x86',
        'armv7l': 'arm', 'armv8l': 'arm64', 'aarch64': 'arm64'
    }
    
    arch = arch_map.get(machine, machine)
    logger.info(f"Detected system: {system} {arch}")
    return system, arch

def install_python_dependencies():
    """Install required Python packages."""
    logger.info("Installing Python dependencies...")
    requirements = ['py7zr', 'tqdm', 'colorama']
    
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', *requirements])
        
        # Create requirements.txt
        with open(SCRIPT_DIR / 'requirements.txt', 'w') as f:
            f.write('\n'.join(requirements))
        
        logger.info("Python dependencies installed successfully.")
    except Exception as e:
        logger.error(f"Failed to install Python dependencies: {e}")
        sys.exit(1)

def download_chdman(system, arch):
    """Download and extract chdman from official MAME distribution."""
    logger.info("Attempting to download chdman from official MAME release...")
    chdman_exec = CHDMAN_DIR / ('chdman.exe' if system == 'windows' else 'chdman')
    
    # Get the latest MAME version
    mame_version = "0.260"  # This would ideally be fetched dynamically
    
    # Official MAME download URLs
    base_url = f"https://github.com/mamedev/mame/releases/download/mame{mame_version}"
    
    # Define download URLs for different platforms
    download_urls = {
        'windows': {
            'x64': f"{base_url}/mame{mame_version}b_64bit.exe",
            'x86': f"{base_url}/mame{mame_version}b_32bit.exe"
        },
        'linux': {
            'x64': f"{base_url}/mame{mame_version}b_64bit.tar.gz",
            'x86': f"{base_url}/mame{mame_version}b_32bit.tar.gz"
        },
        'darwin': {  # macOS
            'x64': f"{base_url}/mame{mame_version}b_64bit.tar.gz",
            'arm64': f"{base_url}/mame{mame_version}b_arm64.tar.gz"
        }
    }
    
    # Check if system/arch combination is supported
    if system in download_urls and arch in download_urls[system]:
        url = download_urls[system][arch]
        
        try:
            # Create temporary directory
            temp_dir = TOOLS_DIR / "temp"
            temp_dir.mkdir(exist_ok=True)
            
            # Download file
            download_path = temp_dir / f"mame_{mame_version}.{'exe' if system == 'windows' else 'tar.gz'}"
            logger.info(f"Downloading MAME from {url}...")
            
            try:
                urllib.request.urlretrieve(url, download_path)
                logger.info("Download completed.")
            except Exception as e:
                logger.error(f"Failed to download MAME: {e}")
                return False
            
            # Extract chdman
            logger.info("Extracting chdman from MAME package...")
            
            if system == 'windows':
                # For Windows, we need to extract chdman.exe from the installer
                # This would require a tool like 7-Zip or similar to extract from the self-extracting exe
                # For now, just inform the user that manual extraction is needed
                logger.warning("Automatic extraction from Windows MAME package not supported.")
                logger.warning("Please extract chdman.exe manually from MAME and place it in:")
                logger.warning(str(CHDMAN_DIR))
                
                # Clean up
                shutil.rmtree(temp_dir)
                return False
                
            else:
                # For Linux/macOS, extract from tar.gz
                import tarfile
                with tarfile.open(download_path, 'r:gz') as tar:
                    for member in tar.getmembers():
                        if member.name.endswith('/chdman') or member.name.endswith('/chdman.exe'):
                            member.name = os.path.basename(member.name)
                            tar.extract(member, CHDMAN_DIR)
                            if system != 'windows':
                                os.chmod(CHDMAN_DIR / "chdman", 0o755)
                            logger.info(f"chdman extracted to {CHDMAN_DIR}")
                            
                            # Clean up
                            shutil.rmtree(temp_dir)
                            return True
                
                logger.warning("chdman not found in the downloaded package.")
            
            # Clean up
            shutil.rmtree(temp_dir)
            
        except Exception as e:
            logger.error(f"Failed to download or extract chdman: {e}")
    
    logger.warning(f"No pre-built chdman available for {system} {arch}")
    return False

def build_chdman(system):
    """Build chdman from official MAME source."""
    logger.info("Building chdman from source...")
    chdman_exec = CHDMAN_DIR / ('chdman.exe' if system == 'windows' else 'chdman')
    
    # MAME version to use
    mame_version = "0.260"  # This should match the version used in download_chdman
    
    # Create a temporary directory for the source code
    temp_dir = TOOLS_DIR / "temp"
    temp_dir.mkdir(exist_ok=True)
    
    # Download MAME source code
    source_url = f"https://github.com/mamedev/mame/archive/refs/tags/mame{mame_version}.tar.gz"
    source_path = temp_dir / f"mame_{mame_version}.tar.gz"
    
    try:
        logger.info(f"Downloading MAME source from {source_url}...")
        urllib.request.urlretrieve(source_url, source_path)
        logger.info("Source code downloaded successfully.")
        
        # Extract source code
        import tarfile
        with tarfile.open(source_path, 'r:gz') as tar:
            tar.extractall(temp_dir)
        
        # Find the source directory
        source_dirs = list(temp_dir.glob('mame*'))
        if not source_dirs:
            logger.error("No source directory found after extraction.")
            shutil.rmtree(temp_dir)
            return False
        
        source_dir = source_dirs[0]
        logger.info(f"Source extracted to {source_dir}")
        
        # Build just chdman
        os.chdir(source_dir)
        logger.info("Building chdman... (this may take a while)")
        
        # Determine build command based on system
        if system == 'windows':
            build_cmd = ['make', 'TOOLS=1', 'SUBTARGET=chdman', '-j4']
            if shutil.which('mingw32-make'):
                build_cmd[0] = 'mingw32-make'
        else:
            build_cmd = ['make', 'TOOLS=1', 'SUBTARGET=chdman', '-j4']
        
        logger.info(f"Running build command: {' '.join(build_cmd)}")
        process = subprocess.run(
            build_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if process.returncode != 0:
            logger.error(f"Build failed with return code {process.returncode}")
            logger.error(f"Error output: {process.stderr}")
            shutil.rmtree(temp_dir)
            return False
        
        # Find and copy the built chdman executable
        for root, _, files in os.walk(source_dir):
            root_path = Path(root)
            for file in files:
                if file == 'chdman.exe' or file == 'chdman':
                    # Copy to our directory
                    src_path = root_path / file
                    shutil.copy2(src_path, chdman_exec)
                    if system != 'windows':
                        os.chmod(chdman_exec, 0o755)
                    logger.info(f"chdman built and copied to {chdman_exec}")
                    
                    # Clean up
                    shutil.rmtree(temp_dir)
                    return True
        
        logger.error("chdman executable not found after build.")
        shutil.rmtree(temp_dir)
        return False
        
    except Exception as e:
        logger.error(f"Failed to build chdman: {e}")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        return False

def find_chdman_in_common_locations(system):
    """
    Search for chdman in common installation locations based on the OS.
    
    Args:
        system (str): The operating system ('windows', 'darwin', 'linux')
        
    Returns:
        Path or None: Path to chdman if found, None otherwise
    """
    logger.info("Searching for chdman in common installation locations...")
    
    # Define common locations based on OS
    if system == 'windows':
        common_locations = [
            Path("C:/Program Files/MAME"),
            Path("C:/Program Files (x86)/MAME"),
            Path(os.environ.get('PROGRAMFILES', "C:/Program Files")) / "MAME",
            Path(os.environ.get('PROGRAMFILES(X86)', "C:/Program Files (x86)")) / "MAME",
            Path.home() / "MAME",
            Path.home() / "emulators" / "MAME"
        ]
        chdman_names = ["chdman.exe"]
    elif system == 'darwin':  # macOS
        common_locations = [
            Path("/Applications/MAME.app/Contents/MacOS"),
            Path.home() / "Applications" / "MAME.app" / "Contents" / "MacOS",
            Path.home() / "emulators" / "mame",
            Path("/usr/local/bin"),
            Path("/usr/local/mame")
        ]
        chdman_names = ["chdman"]
    else:  # Linux and others
        common_locations = [
            Path("/usr/bin"),
            Path("/usr/local/bin"),
            Path("/opt/mame"),
            Path.home() / ".mame",
            Path.home() / "mame",
            Path.home() / "emulators" / "mame"
        ]
        chdman_names = ["chdman"]
    
    # Search in common locations
    for location in common_locations:
        if location.exists() and location.is_dir():
            for name in chdman_names:
                chdman_path = location / name
                if chdman_path.exists() and os.access(chdman_path, os.X_OK if system != 'windows' else os.F_OK):
                    logger.info(f"Found chdman at: {chdman_path}")
                    return chdman_path
                
                # Also look in subdirectories one level deep
                for subdir in location.iterdir():
                    if subdir.is_dir():
                        chdman_subpath = subdir / name
                        if chdman_subpath.exists() and os.access(chdman_subpath, os.X_OK if system != 'windows' else os.F_OK):
                            logger.info(f"Found chdman at: {chdman_subpath}")
                            return chdman_subpath
    
    logger.info("chdman not found in common locations")
    return None

def prompt_for_chdman_path(system):
    """
    Prompt the user to specify the path to chdman.
    
    Args:
        system (str): The operating system ('windows', 'darwin', 'linux')
        
    Returns:
        Path or None: Path to chdman if provided and valid, None otherwise
    """
    chdman_exec_name = 'chdman.exe' if system == 'windows' else 'chdman'
    
    print("\n" + "="*60)
    print("chdman not found automatically.")
    print("chdman is required for CHD conversion and is typically included with MAME.")
    print("Please enter the path to the chdman executable:")
    print("Example: C:\\path\\to\\chdman.exe" if system == 'windows' else "/path/to/chdman")
    print("="*60)
    
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
            if system != 'windows' and not os.access(chdman_path, os.X_OK):
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
    
    system, arch = get_system_info()
    chdman_exec = CHDMAN_DIR / ('chdman.exe' if system == 'windows' else 'chdman')
    
    # Check if chdman is already configured
    config_file = SCRIPT_DIR / "chdman_path.txt"
    if config_file.exists():
        with open(config_file, 'r') as f:
            chdman_path = f.read().strip()
            if os.path.exists(chdman_path):
                logger.info(f"Using previously configured chdman at: {chdman_path}")
                return True
    
    # Check if chdman is in PATH
    chdman_in_path = shutil.which('chdman')
    if chdman_in_path:
        logger.info(f"Found chdman in PATH: {chdman_in_path}")
        # Store the path rather than copying
        with open(config_file, 'w') as f:
            f.write(chdman_in_path)
        return True
    
    # Try to find chdman in common locations
    chdman_path = find_chdman_in_common_locations(system)
    if chdman_path:
        logger.info(f"Using chdman from common location: {chdman_path}")
        # Copy to our directory
        shutil.copy2(chdman_path, chdman_exec)
        if system != 'windows':
            os.chmod(chdman_exec, 0o755)
        return True
    
    # Try to download pre-built binary
    if download_chdman(system, arch):
        logger.info("chdman downloaded successfully.")
        return True
    
    # Try to build from source
    if build_chdman(system):
        logger.info("chdman built successfully.")
        return True
    
    # Prompt the user for the path to chdman
    chdman_path = prompt_for_chdman_path(system)
    if chdman_path:
        # Store the path rather than copying
        config_file = SCRIPT_DIR / "chdman_path.txt"
        with open(config_file, 'w') as f:
            f.write(str(chdman_path))
        logger.info(f"Stored chdman path in configuration: {chdman_path}")
        return True
    
    # Store the path to user-provided chdman in a configuration file
    if chdman_path:
        config_file = SCRIPT_DIR / "chdman_path.txt"
        with open(config_file, 'w') as f:
            f.write(str(chdman_path))
        logger.info(f"chdman path stored in configuration file: {config_file}")
        return True
    
    logger.warning("Could not set up chdman automatically.")
    logger.warning("You will be prompted for the chdman path when running the conversion.")
    return False

def main():
    """Main setup function."""
    logger.info("Starting 7z-to-CHD Converter setup...")
    
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
            logger.warning("chdman was not found or configured. You'll need to provide its path during conversion.")
        
        logger.info("You can now run 'convert.py' to start the conversion process.")
    
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()