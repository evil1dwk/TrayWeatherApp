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
        owner=SimpleNamespace(config={"tray_display":"temperature"},theme=ThemeManager(),cities=["Boston","London"],
                              locations={},jobs={},units="imperial",tray=Mock(),save_config=Mock())
        window=WeatherWindow(owner)
        window.add_city_tab("Boston");window.add_city_tab("London");window.add_fake_tab()
        with patch("TrayWeatherApp.weather.create_temperature_icon") as icon:
            window.update_city_tab("Boston",{"city":"Boston, US","temp":68.7,"desc":"Clear sky","icon":"☀️"})
            window.update_city_tab("London",{"city":"London, UK","temp":50,"desc":"Rain","icon":"🌧️"})
            self.assertEqual(icon.call_args.args,(68.7,))
            self.assertIn("68.7°F",owner.tray.setToolTip.call_args.args[0])
            window.tabs.tabBar().moveTab(1,0)
            self.assertEqual(owner.cities,["London","Boston"])
            self.assertEqual(icon.call_args.args,(50,))
            window.remove_tab(0)
            self.assertEqual(icon.call_args.args,(68.7,))
            window.clear_weather("Boston")
            self.assertEqual(icon.call_args.args,(None,))
            window.remove_tab(0)
            self.assertIn("No cities",owner.tray.setToolTip.call_args.args[0])
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)

    def test_temperature_uses_large_digits_without_degree_symbol(self):
        from PyQt6.QtGui import QPainter, QPainterPath
        captured = []
        bounds = []
        class RecordingPath(QPainterPath):
            def addText(self, *args):
                captured.append(args)
                return super().addText(*args)
        class RecordingPainter(QPainter):
            def drawPath(self, path):
                bounds.append(path.boundingRect())
                return super().drawPath(path)
        with patch("PyQt6.QtGui.QPainterPath", RecordingPath), patch(
                "TrayWeatherApp.config_utils.QPainter", RecordingPainter):
            for value in (68.7, -13, 105, None):
                create_temperature_icon(value)
        self.assertEqual(captured[0][2], "69")
        for args, rect in zip(captured, bounds):
            self.assertTrue(args[1].bold())
            self.assertLessEqual(rect.width(), 58.01)
            self.assertLessEqual(rect.height(), 54.01)
            self.assertTrue(abs(rect.width() - 58) < .01 or abs(rect.height() - 54) < .01)
            self.assertAlmostEqual(rect.center().x(), 32)
            self.assertAlmostEqual(rect.center().y(), 32)

    def test_icon_default_and_temperature_option_use_same_tooltip(self):
        owner=SimpleNamespace(config={},theme=ThemeManager(),cities=["Boston"],locations={},
                              jobs={},units="imperial",tray=Mock(),save_config=Mock())
        window=WeatherWindow(owner);window.add_city_tab("Boston")
        with patch("TrayWeatherApp.weather.create_tray_icon") as emoji, patch(
                "TrayWeatherApp.weather.create_temperature_icon") as digits:
            window.update_city_tab("Boston",{"city":"Boston","temp":69,"icon":"☀️","desc":"Clear sky"})
            emoji.assert_called_with("☀️")
            digits.assert_not_called()
            tooltip=owner.tray.setToolTip.call_args.args[0]
            owner.config["tray_display"]="temperature"
            window.update_tray_temperature()
            digits.assert_called_with(69)
            self.assertEqual(owner.tray.setToolTip.call_args.args[0],tooltip)
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)

    def test_settings_tray_choice_is_saved_only_on_accept(self):
        from TrayWeatherApp.settings import SettingsDialog
        config={}
        dialog=SettingsDialog(config,ThemeManager())
        self.assertEqual(dialog.tray_select.currentData(),"icon")
        dialog.tray_select.setCurrentIndex(1)
        self.assertEqual(dialog.get_values()["tray_display"],"temperature")
        dialog.reject()
        self.assertNotIn("tray_display",config)
        dialog.deleteLater()
