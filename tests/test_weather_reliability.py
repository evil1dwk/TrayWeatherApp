import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PyQt6.QtCore import QObject, QEventLoop, QTimer, QCoreApplication, QEvent, QThread
from PyQt6.QtWidgets import QApplication
from TrayWeatherApp.app import TrayWeatherApp
from TrayWeatherApp.theme import ThemeManager
from TrayWeatherApp.weather import WeatherWindow
from TrayWeatherApp.weather_cache import WeatherCache
from TrayWeatherApp.workers import WeatherWorker, location_label, search_locations
from TrayWeatherApp.city_search import CitySearchDialog

LOCATION = {"id": 123, "name": "Springfield", "admin1": "Illinois", "country": "United States",
            "latitude": 39.8, "longitude": -89.6}


def weather(minutes=0):
    return {"city": "Springfield, Illinois, United States", "temp": 20, "high": 22, "units": "metric",
            "location": LOCATION, "updated_at": (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()}


class CacheTests(unittest.TestCase):
    def test_round_trip_units_coordinates_and_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cache.json"
            cache = WeatherCache(path)
            cache.put("city", "metric", weather(), LOCATION)
            loaded = WeatherCache(path)
            self.assertEqual(loaded.get("city", "metric", LOCATION)["temp"], 20)
            self.assertIsNone(loaded.get("city", "imperial", LOCATION))
            self.assertIsNone(loaded.get("city", "metric", {**LOCATION, "latitude": 40}))
            self.assertIsNone(loaded.get("other", "metric", LOCATION))
            path.write_text(json.dumps({"broken": {"updated_at": 123}, "other": []}))
            loaded = WeatherCache(path)
            loaded.put("city", "metric", weather(), LOCATION)
            self.assertEqual(len(loaded.entries), 1)
            path.write_text("corrupt")
            self.assertIsNone(WeatherCache(path).get("city", "metric", LOCATION))

    def test_invalid_response_does_not_overwrite_good_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = WeatherCache(Path(directory) / "cache.json")
            cache.put("city", "metric", weather())
            cache.put("city", "metric", {"temp": None, "updated_at": "bad"})
            self.assertEqual(cache.get("city", "metric")["temp"], 20)


class WeatherReliabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.owner = TrayWeatherApp.__new__(TrayWeatherApp)
        QObject.__init__(self.owner)
        self.owner.app = self.qt
        self.owner.theme = ThemeManager()
        self.owner.config = {}
        self.owner.locations = {"city": LOCATION}
        self.owner.cities = ["city"]
        self.owner.units = "metric"
        self.owner.jobs = {}
        self.owner._threads = set()
        self.owner._quitting = False
        self.owner.tray = None
        self.owner.save_config = Mock()
        self.owner.cache = WeatherCache(Path(self.temporary.name) / "cache.json")
        self.owner.window = WeatherWindow(self.owner)
        self.owner.window.add_city_tab("city")

    def tearDown(self):
        self.owner.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.temporary.cleanup()

    def test_failure_keeps_previous_weather_and_reports_age(self):
        self.owner.window.update_city_tab("city", weather(45))
        self.owner.jobs["city"] = {"token": "request", "units": "metric"}
        self.owner.weather_result("city", {"request_id": "request", "units": "metric", "error": "timeout"})
        card = self.owner.window.city_tabs["city"]["card"]
        self.assertEqual(card.temp_lbl.text(), "20.0°C")
        self.assertIn("saved weather", card.status_lbl.text())
        self.assertIn("stale", card.status_lbl.text())
        self.assertEqual(card.status_lbl.toolTip(), "timeout")

    def test_first_failure_without_cache_is_explicit(self):
        self.owner.window.set_weather_state("city", "error", "timeout")
        card = self.owner.window.city_tabs["city"]["card"]
        self.assertIn("no saved weather", card.status_lbl.text())
        self.assertEqual(card.temp_lbl.text(), "-°")

    def test_late_result_after_unit_change_or_city_removal_is_ignored(self):
        self.owner.jobs["city"] = {"token": "new", "units": "metric"}
        self.owner.weather_result("city", {**weather(), "request_id": "old"})
        self.assertNotIn("info", self.owner.window.city_tabs["city"])
        self.owner.weather_result("city", {**weather(), "request_id": "new", "units": "imperial"})
        self.assertNotIn("info", self.owner.window.city_tabs["city"])
        self.owner.jobs.clear()
        self.owner.weather_result("city", {**weather(), "request_id": "new"})
        self.assertNotIn("info", self.owner.window.city_tabs["city"])

    def test_success_caches_and_marks_updated(self):
        self.owner.jobs["city"] = {"token": "request", "units": "metric"}
        self.owner.weather_result("city", {**weather(), "request_id": "request"})
        self.assertIn("Up to date", self.owner.window.city_tabs["city"]["card"].status_lbl.text())
        self.assertEqual(self.owner.cache.get("city", "metric", LOCATION)["temp"], 20)

    def test_selected_coordinates_bypass_geocoding(self):
        worker = WeatherWorker("city", "metric", LOCATION, "request")
        response = Mock(status_code=200)
        response.json.return_value = {"current": {"temperature_2m": 20}, "daily": {}}
        results = []
        worker.result.connect(lambda city, result: results.append(result))
        with patch("TrayWeatherApp.workers.requests.get", return_value=response) as get:
            worker.run()
        get.assert_called_once()
        self.assertEqual(get.call_args.kwargs["params"]["latitude"], LOCATION["latitude"])
        self.assertEqual(results[0]["city"], location_label(LOCATION))
        self.assertIn("updated_at", results[0])

    def test_background_refresh_restores_cache_then_updates_on_gui_thread(self):
        self.owner.cache.put("city", "metric", weather(40), LOCATION)
        gui_thread = QThread.currentThread()
        completion_threads = []
        original = self.owner.window.update_city_tab
        self.owner.window.update_city_tab = lambda *args: (completion_threads.append(QThread.currentThread()), original(*args))
        response = Mock(status_code=200)
        response.json.return_value = {"current": {"temperature_2m": 25}, "daily": {}}
        with patch("TrayWeatherApp.workers.requests.get", return_value=response):
            self.owner.fetch_weather_city("city")
            card = self.owner.window.city_tabs["city"]["card"]
            self.assertEqual(card.temp_lbl.text(), "20.0°C")
            self.assertIn("Refreshing", card.status_lbl.text())
            loop = QEventLoop()
            timer = QTimer()
            timer.setInterval(5)
            timer.timeout.connect(lambda: loop.quit() if not self.owner._threads else None)
            timer.start()
            QTimer.singleShot(3000, loop.quit)
            loop.exec()
            timer.stop()
        self.assertFalse(self.owner._threads, "worker did not complete")
        self.assertEqual(card.temp_lbl.text(), "25.0°C")
        self.assertTrue(all(thread == gui_thread for thread in completion_threads))

    def test_city_selection_persists_coordinates_and_prevents_duplicate(self):
        self.owner.fetch_weather_city = Mock()
        self.owner.add_location(LOCATION)
        self.owner.add_location(LOCATION)
        self.assertEqual(self.owner.cities, ["city"])
        self.assertEqual(self.owner.locations["city"], LOCATION)
        self.owner.fetch_weather_city.assert_not_called()
        other = {**LOCATION, "id": 456, "latitude": 42.1}
        self.owner.add_location(other)
        self.assertEqual(self.owner.locations["geo:456"], other)
        self.owner.fetch_weather_city.assert_called_once_with("geo:456")

    def test_search_results_disambiguate_and_require_selection(self):
        dialog = CitySearchDialog()
        locations = [LOCATION, {**LOCATION, "id": 456, "admin1": "Massachusetts"}]
        dialog.show_results(locations, "")
        self.assertIn("Illinois", dialog.results.item(0).text())
        self.assertIn("Massachusetts", dialog.results.item(1).text())
        self.assertFalse(dialog.add_button.isEnabled())
        dialog.results.setCurrentRow(1)
        dialog.accept()
        self.assertEqual(dialog.selected_location["id"], 456)
        dialog.deleteLater()

    def test_location_search_returns_multiple_valid_matches(self):
        response = Mock()
        response.json.return_value = {"results": [LOCATION, {"name": "invalid"}]}
        with patch("TrayWeatherApp.workers.requests.get", return_value=response) as get:
            self.assertEqual(search_locations("Springfield"), [LOCATION])
        self.assertEqual(get.call_args.kwargs["params"]["count"], 10)


    def test_empty_window_plus_can_still_add_city(self):
        window = self.owner.window
        window.add_fake_tab()
        window.remove_tab(0)
        with patch("TrayWeatherApp.weather.CitySearchDialog") as dialog:
            dialog.return_value.exec.return_value = 0
            window.click_tab(0)
            dialog.assert_called_once()

    def test_cancel_while_refreshing_leaves_thread_alive_until_completion(self):
        response = Mock(status_code=200)
        response.json.return_value = {"current": {"temperature_2m": 25}, "daily": {}}
        with patch("TrayWeatherApp.workers.requests.get", return_value=response):
            self.owner.fetch_weather_city("city")
            self.owner.cleanup_job("city")
            self.assertFalse(self.owner.jobs)
            loop = QEventLoop()
            poll = QTimer()
            poll.setInterval(5)
            poll.timeout.connect(lambda: loop.quit() if not self.owner._threads else None)
            poll.start()
            QTimer.singleShot(3000, loop.quit)
            loop.exec()
            poll.stop()
        self.assertFalse(self.owner._threads)
        self.assertNotIn("info", self.owner.window.city_tabs["city"])


    def test_adding_first_city_to_placeholder_does_not_open_nested_dialog(self):
        window = self.owner.window
        window.add_fake_tab()
        window.remove_tab(0)
        self.owner.fetch_weather_city = Mock()
        with patch("TrayWeatherApp.weather.CitySearchDialog") as dialog:
            self.owner.add_location(LOCATION)
        dialog.assert_not_called()
        self.assertEqual(self.owner.cities, ["geo:123"])
        self.assertEqual(window.tabs.currentIndex(), 0)
