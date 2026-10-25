# Changelog

## 2.2.1

- Fix a crash when saving Settings after closing a city tab whose displayed name changed after a weather update.
- Clean up the original city record and background job when closing a renamed tab.
- Keep the add-city placeholder when closing tabs, without opening an unexpected Add City dialog.
- Add offscreen Qt regression tests for tab removal and Settings updates.

## 2.2.0

- Added editable Python package installation and optional build dependencies.
- Unified module and console entry points, with a version command.
- Centralized MAJOR.MINOR.PATCH versioning; builds do not change the version.
- Added unit tests and a manual cross-platform test workflow.
- Moved build tooling to scripts/ and platform configuration to packaging/.
- Build executables and versioned ZIP (Windows) or tar.gz (Linux) archives into dist/.
- Removed the Windows installer build.
- Store generated themes in the user profile when no portable theme ZIPs exist.

## 2.1.4

Previous application version. See Git history for historical changes.
