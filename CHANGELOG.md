# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Development tooling (black, flake8, mypy, pytest)
- Modern pyproject.toml configuration
- Centralized version management
- Risk disclaimer in README
- Enhanced installation instructions
- Security and privacy documentation
- Code quality tools and pre-commit hooks

### Changed
- Improved README with badges and better structure
- Enhanced documentation sections
- Better .gitignore for Python projects

## [1.0.2] - 2024-XX-XX

### Fixed
- Fixed playlist updates for games with more than two discs

## [1.0.1] - 2024-XX-XX

### Fixed  
- Fixed playlist generation for games with more than two discs

## [1.0.0] - 2024-XX-XX

### Added
- Initial release
- Cross-platform support (Windows, macOS, Linux)
- Batch processing of .7z archives to CHD format
- Multi-disc game detection and .m3u playlist creation
- Resume functionality to avoid redundant processing
- Multithreading support with adaptive resource allocation
- Detailed logging for troubleshooting
- Automatic chdman detection and configuration
- Command-line interface with interactive prompts

### Features
- Extract files from .7z archives with smart resource management
- Convert disc image formats (ISO, BIN/CUE, GDI, NRG, etc.) to CHD
- Create .m3u playlists for multi-disk games automatically
- Cross-platform compatibility
- Efficient resume functionality
- Comprehensive error handling and logging

[Unreleased]: https://github.com/AKSDug/7z-to-chd/compare/v1.0.2...HEAD
[1.0.2]: https://github.com/AKSDug/7z-to-chd/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/AKSDug/7z-to-chd/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/AKSDug/7z-to-chd/releases/tag/v1.0.0