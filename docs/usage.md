# User guide

[README](../README.md) · [User guide](usage.md) · [Customization](customization.md) · [Development](development.md)

## Tray window controls

The weather panel has no title bar or minimize/maximize/close buttons. Click the
tray icon to show or hide it, and drag the panel background or weather text to
move it. Tab buttons, Settings gears, and links keep their usual actions.
Positions and the selected city tab are saved when hiding or quitting.
Startup restores that city, or the first tab if the saved city is unavailable. Use **Quit** in the tray menu to
exit; Alt+F4 hides the panel. Settings and other dialogs retain normal controls.

## Normal and Compact views

Choose **Normal** or **Compact** under **View** in Settings. Both layouts keep the
weather icon visible and use a fixed window size; manual resizing and maximizing
are disabled. Save applies and remembers your choice. Cancel leaves the current
view unchanged. The Settings preview also reflects the selected view when enough screen space is available.
Settings has no scroll area; on short screens the preview is hidden to keep controls accessible.

Normal uses 760 × 500 logical pixels; Compact uses 440 × 240.
Compact is a horizontal summary with a small icon, city, temperature, conditions,
feels-like/high/low line, and update footer. Hover for the full location,
humidity, wind, local city time, or detailed update status. The footer gear opens
Settings. Existing saved window
positions are retained. Older arbitrary window sizes are replaced by the chosen
view size.

## Tray display

Settings offers **Weather icon** (default) or **Temperature only**. Save applies
and remembers the choice; Cancel leaves it unchanged. Both use the leftmost city
tab. Drag city tabs to change the tray city.

Weather icon displays only the weather emoji. Temperature only uses large
outlined digits, without a degree symbol. In both modes, hover for the exact
temperature with units, location, conditions, and update status.

## Daily forecast

Use **Current / Forecast** below the city tabs. Normal shows five days and
Compact also shows five, without changing the window size or selected city. The
selection is remembered across cities and restarts.

Each day shows its weather icon and high/low temperatures in your selected unit
system. Normal also shows precipitation probability; hover over a day in either
view for its full date, conditions, and precipitation chance. The first day is
the current date at the selected location, followed by subsequent days.

Forecast data arrives in the same request as current weather and is cached
together. Switching views does not make another request. Existing caches without
forecast data show an unavailable message until the next successful refresh.
Saved forecasts remain visible after a failed refresh, with the shared footer
showing their age and error state.

## Weather freshness and cities

Each weather card shows the last successful download in your computer's local
time, its age, and whether it is up to date, refreshing, cached, or unable to
refresh. Readings become stale after 30 minutes. An error keeps the last good
weather visible; hover over the status for the error details.

Successful results are saved to ~/.TrayWeatherApp/weather-cache.json and restored
immediately at startup while a fresh request runs. The cache is separate for each
location and unit system. It is bounded to 200 entries and may be deleted to reset it.

Click **+** to search cities or postal codes. Select a result showing its
state/province, country, and coordinates. Selected coordinates are saved so future
refreshes use that exact location. Existing city-name settings continue to work;
their coordinates are remembered after the next successful refresh. To correct an
old ambiguous city, remove its tab and add it again through the search dialog.

## Linux window positioning

On Linux, the application defaults to Qt's xcb backend when DISPLAY is available.
On a Wayland desktop this uses XWayland, allowing the app to query and restore
window positions. XWayland and Qt's X11 runtime dependencies must be installed.
The same startup behavior applies to source and standalone executable launches.

You can test it explicitly:

    QT_QPA_PLATFORM=xcb python -m TrayWeatherApp

An explicit QT_QPA_PLATFORM setting is preserved. To opt back into native Wayland:

    QT_QPA_PLATFORM=wayland python -m TrayWeatherApp

Native Wayland may prevent applications from restoring top-level window positions.
Window geometry is saved when quitting through the tray menu.

