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
        self.assertEqual(self.window.tabs.tabText(index), "Boston")
        # Removal must still work if a label is changed independently.
        self.window.tabs.setTabText(index, "Boston, US")
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

    def test_city_name_and_fixed_views_keep_icon_and_text_visible(self):
        self.window.update_city_tab("Boston", {
            "city": "Chase City, Virginia, United States",
            "location": {"name": "Chase City"}, "temp": 20, "wind_speed": 6.6})
        data = self.window.city_tabs["Boston"]
        card = data["card"]
        self.assertEqual(card.city_lbl.text(), "Chase City")
        self.assertEqual(self.window.tabs.tabText(0), "Chase City")
        self.assertIn("Virginia", card.city_lbl.toolTip())
        self.window.show()
        for mode, size in [("normal", (760, 500)), ("compact", (440, 240))]:
            self.owner.config["view_mode"] = mode
            self.window.apply_view_mode()
            self.qt.processEvents()
            self.assertEqual((self.window.width(), self.window.height()), size)
            self.assertEqual(self.window.minimumSize(), self.window.maximumSize())
            self.window.resize(1100, 800)
            self.qt.processEvents()
            self.assertEqual((self.window.width(), self.window.height()), size)
            self.assertFalse(card.icon_lbl.isHidden())
            if mode == "normal":
                self.assertGreaterEqual(card.more_lbl.height(), card.more_lbl.heightForWidth(card.more_lbl.width()))
            else:
                self.assertFalse(card.compact_icon.isHidden())
                self.assertTrue(card.normal_panel.isHidden())
                self.assertEqual(card.compact_city.text(), "Chase City")
                self.assertIn("High", card.compact_summary.text())
        self.assertIn("<table", card.more_lbl.text())

    def test_compact_summary_tooltips_and_settings_button(self):
        from TrayWeatherApp.ui_components import GlassCard
        callback = Mock()
        owner = SimpleNamespace(theme=self.owner.theme, config={"view_mode": "compact"},
                                open_settings=callback)
        card = GlassCard(owner)
        card.city_lbl.setText("Chase City")
        card.city_lbl.setToolTip("Chase City, Virginia, United States")
        card.more_lbl.setText(card.themed_detail_html(65.1, 69, 43.4, 42, 6.5, "F", "mph"))
        card.temp_lbl.setText("68.7°F")
        card.sync_compact()
        self.assertEqual(card.compact_temp.text(), "68.7°F")
        self.assertIn("Feels 65°", card.compact_summary.text())
        self.assertNotIn("Humidity", card.compact_summary.text())
        self.assertIn("Humidity: 42%", card.compact_summary.toolTip())
        self.assertIn("Wind: 6.5 mph", card.compact_summary.toolTip())
        self.assertIn("Virginia", card.compact_city.toolTip())
        card.settings_button.click()
        callback.assert_called_once()
        card.deleteLater()

    def test_shared_footer_tracks_selected_city_outside_card(self):
        from datetime import datetime, timezone
        self.window.update_city_tab("Boston", {"city": "Boston", "temp": 20,
                                              "updated_at": datetime.now(timezone.utc).isoformat()})
        self.window.set_weather_state("Boston", "live")
        self.window.tabs.setCurrentWidget(self.window.city_tabs["Boston"]["container"])
        self.assertIn("Up to date", self.window.footer_status.text())
        self.assertTrue(self.window.city_tabs["Boston"]["card"].status_lbl.isHidden())
        self.window.tabs.setCurrentWidget(self.window.city_tabs["London"]["container"])
        self.assertIn("Waiting", self.window.footer_status.text())
        self.window.set_weather_state("London", "error", "timeout")
        self.assertIn("Unable", self.window.footer_status.text())
        self.assertIn("timeout", self.window.footer_status.toolTip())

    def test_normal_settings_gear_opens_settings(self):
        from TrayWeatherApp.ui_components import GlassCard
        callback = Mock()
        card = GlassCard(SimpleNamespace(theme=self.owner.theme,
                                        config={"view_mode": "normal"}, open_settings=callback))
        card.show()
        self.qt.processEvents()
        self.assertTrue(card.normal_settings_button.isVisible())
        self.assertFalse(card.settings_button.isVisible())
        self.assertEqual(card.normal_settings_button.toolTip(), "Settings")
        card.normal_settings_button.click()
        callback.assert_called_once()
        card.close()
        card.deleteLater()
