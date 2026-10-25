# Changelog

## 2.3.0 — planned first release

- Add background opacity (60–100%) and optional 20 px rounded window corners in Settings; text remains opaque.
- Replaced generated theme ZIPs with eight bundled, validated JSON presets.
- Added System appearance, custom theme import/export, and a custom themes folder.
- Added an isolated Settings preview; Save applies a theme and Cancel preserves the active theme.
- Preserve legacy ZIP imports, optional CSS, and existing saved theme selections.
- Centralized theme notifications and recolor existing weather details when themes change.
- Added About TrayWeatherApp with the visible version and project links.
- Added theme format documentation and regression tests.
- Add Current / Forecast switching with five daily forecasts in both Normal and Compact.
- Fetch and cache forecasts with current weather, including precipitation chance and hover details.
- Add Weather icon (default) and Temperature only tray display choices in Settings.
- Show last successful weather download, freshness, cached/offline state, and refresh errors.
- Cache successful readings by location and units; preserve them when refresh fails.
- Add background city search with state/province/country choices and saved coordinates.
- Show city-only labels with full-location tooltips and use aligned weather-card details.
- Add fixed Normal and Compact views in Settings, retaining the weather icon in both layouts.
- Make Compact a 440 × 240 horizontal summary with hover details and a Settings gear.
- Deliver weather updates on the GUI thread and ignore stale results after tab/unit changes.
- Keep active request threads alive until they finish when closing tabs or quitting.
- Default Linux launches to xcb/XWayland when an X display is available, preserving explicit platform overrides.

Earlier entries record development milestones, not published releases.

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
