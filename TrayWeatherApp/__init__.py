"""TrayWeatherApp package."""
from ._version import __version__

__all__ = ["__version__"]

# Preserve existing imports without loading Qt or writing settings on package import.
def __getattr__(name):
    import importlib
    modules = {
        "TrayWeatherApp": "app",
        "ThemeManager": "theme",
        "WeatherWindow": "weather",
        "SettingsDialog": "settings",
        "GlassCard": "ui_components",
        "WeatherWorker": "workers",
    }
    if name not in modules:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(importlib.import_module(f".{modules[name]}", __name__), name)
    globals()[name] = value
    return value


__all__ += ["TrayWeatherApp", "ThemeManager", "WeatherWindow",
            "SettingsDialog", "GlassCard", "WeatherWorker"]
