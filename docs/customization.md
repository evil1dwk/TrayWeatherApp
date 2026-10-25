# Customization and configuration

[README](../README.md) · [User guide](usage.md) · [Customization](customization.md) · [Development](development.md)

## Appearance

Settings offers **Background opacity** from 60–100% (default 100%) and
**Rounded window corners** (enabled by default, 20 logical pixels).
Background transparency leaves text and icons fully opaque. Save applies and
remembers the choices; Cancel preserves the current appearance. The preview
reflects both options when visible. Desktop compositing is needed for transparency.

## Themes

Choose **System**, **Light**, **Dark**, or one of the other bundled presets in
Settings. System follows the OS appearance preference when available, with Dark
as its fallback. Existing saved selections are retained.

Settings shows a sample weather card before you Save. Cancel leaves the running
theme unchanged. Use **Import Theme**, **Export Theme**, and **Open Themes Folder**
to manage custom JSON themes or import existing theme ZIPs.

Built-in themes ship inside the application. Custom themes live under
~/.TrayWeatherApp/themes/; settings retain their existing location at
~/.TrayWeatherApp/pyqt_tray_weather.json (under your user profile on Windows).
See [Theme format and compatibility](themes.md) for examples and details.

The **About** button at the bottom-left of Settings shows the current application version,
creator, project link, and issue link.


## ⚙️ Configuration File

TrayWeatherApp saves user settings in a JSON file:
```json
{
  "cities": ["New York"],
  "units": "imperial",
  "window_pos": [722, 575],
  "window_size": [760, 500],
  "view_mode": "normal",
  "tray_display": "icon",
  "selected_city": "New York",
  "forecast_mode": false,
  "background_opacity": 100,
  "rounded_corners": true,
  "debug": false,
  "time_format_24h": false,
  "theme": "Dark"
}
```
You can delete this file to reset settings.


