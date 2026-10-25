# Themes

TrayWeatherApp 2.3.0 ships eight built-in themes: Dark, Light, Solarized, Beach,
Forest Mist, Carbon Fiber, Red, and Aurora Borealis. Built-ins are read-only
package data, available from source, an installed wheel, or a standalone build.

**System** is the default for new settings. It follows Qt's operating-system
Light/Dark preference and updates when the OS reports a change. If that preference
is unavailable or unknown, it uses Dark. Linux support depends on Qt and the
desktop's color-scheme integration.

## Settings

Choose a theme to see a sample weather card. The preview, including units and
clock format, is isolated from the running weather window. Save applies the
selection throughout the app; Cancel leaves the active selection unchanged.

Import Theme accepts JSON or existing theme ZIPs. Imports are validated and
converted into JSON under ~/.TrayWeatherApp/themes/ (the Windows user profile
contains the same .TrayWeatherApp folder). Importing a theme is a file operation:
the imported file remains available even if you subsequently cancel Settings.

Export Theme writes the previewed theme as JSON. For System, the export captures
its currently resolved Light or Dark preset. Open Themes Folder opens the custom
theme directory.

Invalid imported files produce readable errors and are not installed. Invalid
previews disable Save. If a saved theme becomes missing or invalid, startup uses
Dark and logs the reason. Reopen Settings to choose another theme.

## JSON format

A minimal custom theme:

    {
      "schema_version": 1,
      "name": "My Ocean",
      "background_gradient": ["#102A43", "#243B53"],
      "text_primary": "#F0F4F8",
      "temp_color": "#FFCA80",
      "link_color": "#80CBC4"
    }

Missing keys inherit Dark defaults. Full examples are in TrayWeatherApp/themes/.
The two-item background_gradient and these color properties control the interface:

| Property | Purpose |
|---|---|
| glass_card_color, card_border_color | Card fill and outline |
| text_primary, text_muted | Main text and clock |
| text_desc, text_more | Weather description and details |
| temp_color, high_color, low_color | Temperature colors |
| humid_color, wind_color | Humidity and wind accents |
| accent_glow, link_color | Weather icon glow and links |
| tab_bg, tab_bg_selected, tab_text, tab_border | City tabs |

Colors accept Qt color names, hex colors, or rgba(r,g,b,a). RGB values must be
0–255. Alpha can be 0–1 or 0–255. Theme names contain 1–80 characters.
schema_version must be 1. Unknown keys are retained for forward compatibility.

An optional css string provides advanced Qt stylesheet overrides after the
generated styles. It can override normal UI styles, so use it sparingly.

## Legacy ZIP compatibility

Existing ZIPs containing one JSON file and at most one CSS file are supported.
CSS is preserved on import as the JSON css property. Archives are read directly;
their contents are never extracted. Theme JSON/CSS content is limited to 1 MiB.

Portable ZIPs beside the application in themes/ remain discoverable. Built-in
names take priority over matching portable names; import a customized ZIP to
retain it as a separately named custom theme. Custom files with a built-in name
are listed with a (custom) suffix. Import automatically chooses a unique name,
so it never overwrites an existing theme or built-in preset.
