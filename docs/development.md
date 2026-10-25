# Development, builds, and releases

[README](../README.md) · [User guide](usage.md) · [Customization](customization.md) · [Development](development.md)

## Installation and development

Requires Python **3.11+** on Windows or Linux. From the repository root:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux: source .venv/bin/activate
python -m pip install -e .
python -m TrayWeatherApp
```

The installed command `trayweatherapp` also launches the app. Use
`python -m TrayWeatherApp --version` to display its version without opening the GUI.
The module name is case-sensitive on Linux.

## Unit tests

```bash
python -m unittest discover -s tests -v
```

Tests include offscreen Qt widget checks, mock weather requests, and use temporary
settings/theme directories; no API
access or running desktop is required. A manual **Unit tests** GitHub Actions
workflow covers Windows, Linux, and macOS with Python 3.11 and 3.14.
macOS test coverage does not imply a supported macOS executable build.

## Building

```bash
python -m pip install -e ".[build]"
python scripts/build.py
# Full build output:
python scripts/build.py --verbose
```

Build on the target operating system. The executable and release archive go to
`dist/`:

- Windows: `TrayWeatherApp.exe` and `TrayWeatherApp-2.3.0-windows-<arch>.zip`
- Linux: `TrayWeatherApp` and `TrayWeatherApp-2.3.0-linux-<arch>.tar.gz`

There is no Windows installer step. Archives contain the standalone executable
and any optional theme ZIPs from `themes/`. Extract before launching. Linux
archives preserve executable permissions. Built-in themes are included inside the executable; no writable application
folder is required.

The build script resolves paths from its own location, so it also works when
invoked by absolute path from another directory. Platform configurations live
in `packaging/windows/build.json` and `packaging/linux/build.json`, matching
TrayNSLookup. Temporary PyInstaller files go to the ignored `build/` folder.

To create an installable Python wheel:

```bash
python -m pip wheel . --no-deps --wheel-dir dist
```

## Versioning

Current version: **2.3.0**. This is the target for the first published release.

`TrayWeatherApp/_version.py` is the single version source for Python package
metadata, the application, and release archive names. Use **MAJOR.MINOR.PATCH**:
major for incompatible changes, minor for compatible additions, patch for fixes.
Builds never increment the version. Release tags should look like `v2.3.0`.
After changing the version, reinstall the editable package with
`python -m pip install -e .` (or `-e ".[build]"`) to refresh installed metadata.

Before publishing, merge the release PR, pull `main`, run the tests, and build on
each target OS. Create tag `v2.3.0` from the tested commit and attach the versioned
ZIP and tar.gz archives from `dist/` to the GitHub release.

## Project layout

- `pyproject.toml`: package metadata, runtime dependencies, and optional build tools
- `TrayWeatherApp/`: application package and module entry point
- `tests/`: standard-library unittest suite
- `scripts/build.py`: executable build and release archive creation
- `packaging/<platform>/build.json`: tracked PyInstaller configuration
- `build/`: temporary build files (ignored)
- `themes/`: optional portable theme ZIP files
- `dist/`: executable and release archive output (ignored)

