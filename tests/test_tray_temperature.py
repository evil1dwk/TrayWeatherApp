import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import unittest
from unittest.mock import Mock,patch
from types import SimpleNamespace
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QCoreApplication,QEvent
from TrayWeatherApp.config_utils import format_tray_temperature,create_temperature_icon
from TrayWeatherApp.weather import WeatherWindow
from TrayWeatherApp.theme import ThemeManager


class TrayTemperatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt=QApplication.instance() or QApplication([])

    def test_temperature_formatting_and_nonempty_icon(self):
        for value,expected in [(68.7,"69°"),(-12.8,"-13°"),(-0.2,"0°"),
                               (105,"105°"),(None,"—"),(float("nan"),"—"),(True,"—")]:
            with self.subTest(value=value):
                self.assertEqual(format_tray_temperature(value),expected)
                pixmap=create_temperature_icon(value).pixmap(64,64)
                self.assertFalse(pixmap.isNull())
                image=pixmap.toImage()
                self.assertTrue(any(image.pixelColor(x,y).alpha()>0 for x in range(64) for y in range(64)))

    def test_first_city_reorder_removal_and_unit_reset(self):
        owner=SimpleNamespace(config={},theme=ThemeManager(),cities=["Boston","London"],
                              locations={},jobs={},units="imperial",tray=Mock(),save_config=Mock())
        window=WeatherWindow(owner)
        window.add_city_tab("Boston");window.add_city_tab("London");window.add_fake_tab()
        with patch("TrayWeatherApp.weather.create_temperature_icon") as icon:
            window.update_city_tab("Boston",{"city":"Boston, US","temp":68.7,"desc":"Clear sky","icon":"☀️"})
            window.update_city_tab("London",{"city":"London, UK","temp":50,"desc":"Rain","icon":"🌧️"})
            self.assertEqual(icon.call_args.args,(68.7,"☀️"))
            self.assertIn("68.7°F",owner.tray.setToolTip.call_args.args[0])
            window.tabs.tabBar().moveTab(1,0)
            self.assertEqual(owner.cities,["London","Boston"])
            self.assertEqual(icon.call_args.args,(50,"🌧️"))
            window.remove_tab(0)
            self.assertEqual(icon.call_args.args,(68.7,"☀️"))
            window.clear_weather("Boston")
            self.assertEqual(icon.call_args.args,(None,"🌍"))
            window.remove_tab(0)
            self.assertIn("No cities",owner.tray.setToolTip.call_args.args[0])
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)

    def test_combined_icon_contains_weather_and_temperature_regions(self):
        for emoji in ("☀️", "🌙", "☁️", "🌧️"):
            image = create_temperature_icon(69, emoji).pixmap(64, 64).toImage()
            with self.subTest(emoji=emoji):
                self.assertTrue(any(image.pixelColor(x,y).alpha() for x in range(64) for y in range(0,32)))
                self.assertTrue(any(image.pixelColor(x,y).alpha() for x in range(64) for y in range(36,64)))
