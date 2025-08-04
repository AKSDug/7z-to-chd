# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.3] - 2025-01-01

### Changed
- **BREAKING**: Default behavior now preserves original files (non-destructive by default)
- Empty input when prompted now defaults to keeping files instead of deleting them
- User must explicitly choose "no" to delete original files
- Updated prompt to show "[default: yes]" for clarity

### Added
- Development tooling (black, flake8, mypy, pytest)
- Modern pyproject.toml configuration
- Centralized version management
- Risk disclaimer in README emphasizing tested safety
- Enhanced installation instructions with virtual environment support
- Security and privacy documentation
- Code quality tools and pre-commit hooks
- GitHub Actions CI pipeline for cross-platform testing
- Comprehensive test suite with 17+ tests

### Fixed
- Critical safety issue where default behavior was destructive
- Misalignment between README claims and actual code behavior
- Code formatting and style consistency across project

### Improved
- README with badges and professional structure
- Documentation clarity around safety and default settings
- Installation methods (manual, virtual env, development)

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

[Unreleased]: https://github.com/AKSDug/7z-to-chd/compare/v1.0.3...HEAD
[1.0.3]: https://github.com/AKSDug/7z-to-chd/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/AKSDug/7z-to-chd/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/AKSDug/7z-to-chd/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/AKSDug/7z-to-chd/releases/tag/v1.0.0