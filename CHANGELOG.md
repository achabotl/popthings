# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## [1.2.0] - 2026-07-24

### Changed

- Migrated packaging from `setup.py` to `pyproject.toml`.
- Raised the minimum supported Python version to 3.12 and test against Python
  3.12, 3.13, and 3.14.
- Updated the GitHub Actions Python setup and packaging workflows.
- Documented running Popthings directly with `uvx` and building releases with
  `uv`.

## [1.1.0] - 2022-03-25

### Added

- Parse dates with negative offsets #4
- Add "how to make a release" section to the README.
- Add Github actions for running tests #6 and publish to PyPI #7.

### Changed

- Formatted with Black #5

## [1.0.1] - 2019-01-26

### Fixed

- Some tasks were incorrectly labeled as projects


[Unreleased]: https://github.com/achabotl/popthings/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/achabotl/popthings/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/achabotl/popthings/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/achabotl/popthings/compare/v1.0.0...v1.0.1
