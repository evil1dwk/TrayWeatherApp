import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import build as builder
from TrayWeatherApp import __version__
from TrayWeatherApp import config_utils
from TrayWeatherApp.theme import ThemeManager
from TrayWeatherApp.workers import WeatherWorker

ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_installed_version_and_entry_point_from_other_directory(self):
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+$")
        self.assertEqual(importlib.metadata.version("TrayWeatherApp"), __version__)
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, "-m", "TrayWeatherApp", "--version"],
                cwd=directory, capture_output=True, text=True, check=True)
        self.assertIn(__version__, result.stdout)

    def test_build_from_other_directory_preserves_source(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            try:
                os.chdir(directory)
                with patch.object(sys, "argv", ["scripts/build.py"]), patch.object(
                    builder, "run_pyinstaller") as run, patch.object(
                    builder, "run_inno_setup"), patch.object(builder, "clean_build_artifacts") as clean:
                    builder.main()
                args = run.call_args.args
                self.assertEqual(Path(args[2]), ROOT)
                self.assertEqual(Path(args[3]), ROOT)
                self.assertIn("TrayWeatherApp/main.py", args[1])
                clean.assert_called_once_with(str(ROOT / ".build"))
            finally:
                os.chdir(previous)
        self.assertTrue((ROOT / "build/windows/build.json").exists())

    def test_build_script_runs_from_scripts_and_other_directory(self):
        self.assertFalse((ROOT / "build.py").exists())
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/build.py"), "--help"],
                cwd=directory, capture_output=True, text=True, check=True)
        self.assertIn("--config", result.stdout)

    def test_pyinstaller_uses_active_interpreter(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(builder.subprocess, "run") as run:
            builder.run_pyinstaller("Example", ["entry.py"], directory, directory)
            self.assertEqual(run.call_args.args[0][:3], [sys.executable, "-m", "PyInstaller"])

    def test_build_configs_do_not_duplicate_version(self):
        for platform in ("windows", "linux"):
            data = json.loads((ROOT / "build" / platform / "build.json").read_text())
            self.assertNotIn("Version", data)


class ConfigurationTests(unittest.TestCase):
    def test_missing_corrupt_and_saved_settings(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            config_utils, "CONFIG_PATH", Path(directory) / "nested/settings.json"):
            defaults = config_utils.load_config()
            defaults["cities"].append("Boston")
            self.assertEqual(config_utils.load_config()["cities"], ["New York"])
            settings = {"cities": ["Boston"], "units": "metric", "theme": "Light"}
            config_utils.save_config(settings)
            self.assertEqual(config_utils.load_config(), settings)
            config_utils.CONFIG_PATH.write_text("invalid json")
            self.assertEqual(config_utils.load_config()["units"], "imperial")


class ThemeTests(unittest.TestCase):
    def test_theme_loading_and_validation(self):
        with tempfile.TemporaryDirectory() as directory, patch("TrayWeatherApp.theme.THEMES_DIR", Path(directory)):
            with zipfile.ZipFile(Path(directory) / "Test.zip", "w") as archive:
                archive.writestr("Test.css", "QWidget { color: red; }")
                archive.writestr("Test.json", '{"text_primary": "#ffffff"}')
            manager = ThemeManager()
            self.assertEqual(manager.list_themes(), ["Test"])
            manager.load_theme("Test")
            self.assertEqual(manager.value("text_primary"), "#ffffff")
            with self.assertRaises(FileNotFoundError):
                manager.load_theme("Missing")
            with zipfile.ZipFile(Path(directory) / "Broken.zip", "w") as archive:
                archive.writestr("Broken.css", "")
            with self.assertRaises(ValueError):
                manager.load_theme("Broken")


class WeatherTests(unittest.TestCase):
    def test_weather_code_day_night_and_unknown(self):
        worker = WeatherWorker("Boston", "metric")
        self.assertEqual(worker.map_weather_code(0), ("Clear sky", "☀️"))
        self.assertEqual(worker.map_weather_code(0, True), ("Clear sky", "🌙"))
        self.assertEqual(worker.map_weather_code(999), ("Unknown", "🌍"))

    def test_fetch_both_unit_systems(self):
        from unittest.mock import Mock
        for units, temperature, wind in [("metric", "celsius", "kmh"), ("imperial", "fahrenheit", "mph")]:
            with self.subTest(units=units):
                worker = WeatherWorker("Boston", units)
                results, errors = [], []
                worker.finished.connect(lambda city, info: results.append((city, info)))
                worker.error.connect(lambda *args: errors.append(args))
                geo = Mock(status_code=200)
                geo.json.return_value = {"results": [{"latitude": 42, "longitude": -71, "name": "Boston", "country_code": "US"}]}
                forecast = Mock(status_code=200)
                forecast.json.return_value = {"current": {"temperature_2m": 12, "weather_code": 3}, "daily": {"temperature_2m_max": [15], "temperature_2m_min": [5]}, "utc_offset_seconds": -14400}
                with patch("TrayWeatherApp.workers.requests.get", side_effect=[geo, forecast]) as get:
                    worker.run()
                self.assertFalse(errors)
                self.assertEqual(results[0][1]["high"], 15)
                self.assertEqual(results[0][1]["city"], "Boston, US")
                params = get.call_args.kwargs["params"]
                self.assertEqual(params["temperature_unit"], temperature)
                self.assertEqual(params["wind_speed_unit"], wind)

    def test_api_errors(self):
        from unittest.mock import Mock
        import requests
        for response, message in [
            (Mock(status_code=503), "Geocode error 503"),
            (Mock(status_code=200, json=lambda: {"results": []}), "City not found"),
            (requests.Timeout("timeout"), "timeout"),
        ]:
            worker = WeatherWorker("Missing", "metric")
            errors = []
            worker.error.connect(lambda city, error: errors.append(error))
            kwargs = {"side_effect": response} if isinstance(response, Exception) else {"return_value": response}
            with patch("TrayWeatherApp.workers.requests.get", **kwargs):
                worker.run()
            self.assertIn(message, errors[0])
