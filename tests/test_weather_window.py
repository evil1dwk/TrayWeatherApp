"""Exercise actual Qt widget ownership without network or a desktop session."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PyQt6 import sip
from PyQt6.QtCore import QCoreApplication, QEvent, QObject
from PyQt6.QtWidgets import QApplication
from TrayWeatherApp.app import TrayWeatherApp
from TrayWeatherApp.theme import ThemeManager
from TrayWeatherApp.weather import WeatherWindow


class WeatherWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def setUp(self):
        self.owner = SimpleNamespace(
            config={}, theme=ThemeManager(), cities=["Boston", "London"],
            units="metric", jobs={"Boston": {}}, save_config=Mock(),
            cleanup_job=Mock(), fetch_weather_city=Mock(), tray=None)
        self.window = WeatherWindow(self.owner)
        for city in self.owner.cities:
            self.window.add_city_tab(city)
        self.window.add_fake_tab()

    def tearDown(self):
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def test_close_renamed_city_then_save_settings(self):
        self.window.update_city_tab("Boston", {"city": "Boston, US", "temp": 12})
        data = self.window.city_tabs["Boston"]
        index = self.window.tabs.indexOf(data["container"])
        self.assertEqual(self.window.tabs.tabText(index), "Boston, US")
        self.window.remove_tab(index)
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.assertTrue(sip.isdeleted(data["card"].city_lbl))

        # Save settings through the same path as the reported crash.
        app = TrayWeatherApp.__new__(TrayWeatherApp)
        QObject.__init__(app)
        app.units = "metric"
        app.app = self.qt
        app.config = self.owner.config
        app.theme = self.owner.theme
        app.window = self.window
        app.save_config = Mock()
        app.fetch_weather_now = Mock()
        with patch("TrayWeatherApp.app.SettingsDialog") as dialog:
            dialog.return_value.exec.return_value = 1
            dialog.return_value.get_values.return_value = {
                "units": "metric", "theme": "Light", "debug": False,
                "time_format_24h": True}
            with patch.object(app.theme, "load_theme"):
                app.open_settings()

        self.assertNotIn("Boston", self.window.city_tabs)
        self.assertNotIn("Boston", self.owner.cities)
        self.owner.cleanup_job.assert_called_once_with("Boston")
        app.fetch_weather_now.assert_called_once()
        self.assertFalse(sip.isdeleted(self.window.city_tabs["London"]["card"].city_lbl))
        # Queued weather updates for a removed city must be ignored.
        self.window.update_city_tab("Boston", {"city": "Boston, US", "temp": 13})

    def test_placeholder_tab_cannot_be_removed(self):
        index = self.window.tabs.count() - 1
        self.window.remove_tab(index)
        self.assertTrue(self.window.has_fake_tab())
        self.assertEqual(set(self.window.city_tabs), {"Boston", "London"})

    def test_close_last_city_does_not_prompt_to_add_city(self):
        with patch("TrayWeatherApp.weather.QInputDialog.getText") as prompt:
            for city in list(self.owner.cities):
                data = self.window.city_tabs[city]
                self.window.remove_tab(self.window.tabs.indexOf(data["container"]))
        prompt.assert_not_called()
        self.assertFalse(self.window.city_tabs)
        self.assertEqual(self.owner.cities, [])
        self.assertTrue(self.window.has_fake_tab())
        self.window.retheme()
