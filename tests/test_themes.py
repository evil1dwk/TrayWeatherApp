"""Theme schema, ZIP compatibility, Settings transactions, and live notifications."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from TrayWeatherApp.theme import ThemeManager, ThemeError, BUILTIN_DIR
from TrayWeatherApp.settings import SettingsDialog


class ThemeSystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def setUp(self):
        self.log_patch = patch("TrayWeatherApp.theme.log")
        self.log_patch.start()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manager = ThemeManager(custom_dir=self.root, legacy_dirs=[])
        self.original_css = self.qt.styleSheet()
        self.original_palette = self.qt.palette()

    def tearDown(self):
        self.qt.setStyleSheet(self.original_css)
        self.qt.setPalette(self.original_palette)
        self.temp.cleanup()
        self.log_patch.stop()

    def test_all_builtins_validate_and_legacy_lowercase_resolves(self):
        self.assertEqual(len(list(BUILTIN_DIR.glob("*.json"))), 8)
        for path in BUILTIN_DIR.glob("*.json"):
            self.manager.load_theme(path.stem.lower())
            self.assertEqual(self.manager.current_name, path.stem)
            self.assertTrue(self.manager.parse_color(self.manager.value("text_primary")).isValid())

    def test_defaults_and_bad_theme_values(self):
        valid = ThemeManager.validate({"name": "Minimal"})
        self.assertIn("wind_color", valid)
        for data in [[], {"schema_version": 2}, {"name": ""},
                     {"text_primary": "nonsense"}, {"temp_color": 12},
                     {"background_gradient": ["red"]},
                     {"glass_card_color": "rgba(999,0,0,1)"},
                     {"css": []}]:
            with self.subTest(data=data), self.assertRaises(ThemeError):
                ThemeManager.validate(data)

    def test_import_export_legacy_zip_and_collision(self):
        source = self.root / "source.zip"
        with zipfile.ZipFile(source, "w") as archive:
            archive.writestr("../Legacy.json", '{"name":"Dark","text_primary":"#abcdef"}')
            archive.writestr("Legacy.css", "QLabel { font-size: 12px; }")
        name = self.manager.import_theme(source)
        self.assertEqual(name, "Dark (1)")
        self.assertNotEqual(self.manager.import_theme(source), name)
        self.manager.load_theme(name)
        self.assertIn("font-size: 12px", self.manager.current_css)
        self.assertFalse((self.root.parent / "Legacy.json").exists())
        exported = self.root / "export.json"
        self.manager.export_theme(name, exported)
        self.assertEqual(ThemeManager.read_theme(exported)["text_primary"], "#abcdef")

    def test_invalid_import_does_not_write_custom_file(self):
        source = self.root / "invalid.json"
        source.write_text('{"name":"Invalid","link_color":"oops"}')
        before = set(self.root.iterdir())
        with self.assertRaises(ThemeError):
            self.manager.import_theme(source)
        self.assertEqual(set(self.root.iterdir()), before)

    def test_invalid_selected_file_falls_back_and_notifies(self):
        (self.root / "Bad.json").write_text("{bad")
        notifications = []
        self.manager.changed.connect(lambda: notifications.append(self.manager.current_name))
        self.manager.select_theme("Bad")
        self.assertEqual(self.manager.current_name, "Dark")
        self.assertIsNotNone(self.manager.last_error)
        self.assertEqual(notifications, ["Dark"])

    def test_system_changes_follow_only_when_system_selected(self):
        with patch.object(self.manager, "_system_preset", return_value="Light"):
            self.manager.select_theme("System")
            self.assertEqual(self.manager.value("name"), "Light")
        with patch.object(self.manager, "_system_preset", return_value="Dark"):
            self.manager._system_changed()
            self.assertEqual(self.manager.value("name"), "Dark")
        self.manager.select_theme("Beach")
        with patch.object(self.manager, "_system_preset", return_value="Light"):
            self.manager._system_changed()
        self.assertEqual(self.manager.current_name, "Beach")

    def test_preview_cancel_does_not_change_live_app_or_selection(self):
        self.manager.select_theme("Dark")
        self.manager.apply_to_app(self.qt)
        original = self.qt.styleSheet()
        dialog = SettingsDialog({"theme": "Dark"}, self.manager)
        dialog.theme_select.setCurrentText("Light")
        self.assertEqual(dialog.preview_theme.value("name"), "Light")
        self.assertEqual(self.manager.current_name, "Dark")
        self.assertEqual(self.qt.styleSheet(), original)
        dialog.reject()
        self.assertEqual(self.manager.current_name, "Dark")
        dialog.deleteLater()

    def test_save_applies_once_and_recolors_existing_weather(self):
        from types import SimpleNamespace
        from TrayWeatherApp.weather import WeatherWindow
        self.manager.select_theme("Dark")
        owner = SimpleNamespace(theme=self.manager, config={}, units="metric",
                                cities=["Boston"], tray=None)
        window = WeatherWindow(owner)
        self.manager.changed.connect(window.retheme)
        window.add_city_tab("Boston")
        window.update_city_tab("Boston", {"city": "Boston, US", "temp": 20, "high": 22})
        before = window.city_tabs["Boston"]["card"].more_lbl.text()
        self.manager.select_theme("Light")
        after = window.city_tabs["Boston"]["card"].more_lbl.text()
        self.assertNotEqual(before, after)
        self.assertIn("#E65100", after)
        window.deleteLater()

    def test_invalid_preview_disables_save(self):
        (self.root / "Invalid.json").write_text('{"name":"Invalid","temp_color":"bad-color"}')
        dialog = SettingsDialog({}, self.manager)
        dialog.theme_select.setCurrentText("Invalid")
        self.assertFalse(dialog.save_button.isEnabled())
        self.assertIn("temp_color", dialog.error_label.text())
        dialog.accept()
        self.assertEqual(dialog.result(), 0)
        dialog.theme_select.setCurrentText("Light")
        self.assertTrue(dialog.save_button.isEnabled())
        dialog.accept()
        self.assertEqual(dialog.get_values()["theme"], "Light")
        self.assertEqual(dialog.result(), 1)
        dialog.deleteLater()

    def test_external_edit_is_reloaded_without_stale_cache(self):
        path = self.root / "Edited.json"
        path.write_text('{"name":"Edited","temp_color":"#123456"}')
        self.manager.load_theme("Edited")
        path.write_text('{"name":"Edited","temp_color":"#654321"}')
        self.manager.load_theme("Edited")
        self.assertEqual(self.manager.value("temp_color"), "#654321")

    def test_oversized_and_ambiguous_archives_are_rejected(self):
        from TrayWeatherApp.theme import MAX_THEME_BYTES
        for filename, entries in [
            ("large.zip", {"theme.json": " " * (MAX_THEME_BYTES + 1)}),
            ("ambiguous.zip", {"one.json": "{}", "two.json": "{}"}),
        ]:
            path = self.root / filename
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
                for name, contents in entries.items():
                    archive.writestr(name, contents)
            with self.subTest(filename=filename), self.assertRaises(ThemeError):
                self.manager.import_theme(path)

    def test_imported_json_and_about_version(self):
        from TrayWeatherApp._version import __version__
        source = self.root / "import.json"
        source.write_text('{"name":"My Ocean","link_color":"#80CBC4"}')
        name = self.manager.import_theme(source)
        self.manager.load_theme(name)
        self.assertEqual(self.manager.value("link_color"), "#80CBC4")
        dialog = SettingsDialog({}, self.manager)
        with patch("TrayWeatherApp.settings.QMessageBox.about") as about:
            dialog.about_button.click()
        self.assertIs(about.call_args.args[0], dialog)
        self.assertIn(__version__, about.call_args.args[2])
        self.assertEqual(dialog.result(), 0)
        dialog.deleteLater()

    def test_view_preview_is_isolated_until_save(self):
        config = {"view_mode": "normal"}
        dialog = SettingsDialog(config, self.manager)
        dialog.view_select.setCurrentIndex(1)
        self.assertEqual(dialog.preview_card.view_mode, "compact")
        self.assertFalse(dialog.preview_card.icon_lbl.isHidden())
        self.assertEqual(config["view_mode"], "normal")
        self.assertEqual(dialog.get_values()["view_mode"], "compact")
        dialog.reject()
        self.assertEqual(config["view_mode"], "normal")
        dialog.deleteLater()

    def test_settings_size_stays_fixed_when_preview_changes(self):
        dialog = SettingsDialog({}, self.manager)
        dialog.show()
        self.qt.processEvents()
        original = dialog.size()
        for index in (1, 0, 1):
            dialog.view_select.setCurrentIndex(index)
            self.qt.processEvents()
            self.assertEqual(dialog.size(), original)
            self.assertEqual(dialog.minimumSize(), dialog.maximumSize())
            self.assertTrue(dialog.save_button.isVisible())
            self.assertLessEqual(dialog.save_button.geometry().bottom(), dialog.height())
        dialog.close()
        dialog.deleteLater()

    def test_small_screen_omits_preview_without_scrollbars_or_hiding_controls(self):
        from PyQt6.QtCore import QRect
        from unittest.mock import Mock
        dialog = SettingsDialog({}, self.manager)
        dialog._settings_screen = Mock()
        dialog._settings_screen.availableGeometry.return_value = QRect(0, 0, 800, 480)
        dialog.show()
        self.qt.processEvents()
        self.assertEqual(dialog.height(), 416)
        from PyQt6.QtWidgets import QScrollArea
        self.assertEqual(dialog.findChildren(QScrollArea), [])
        self.assertTrue(dialog.preview_frame.isHidden())
        for control in (dialog.units_input, dialog.theme_select, dialog.view_select,
                        dialog.tray_select, dialog.about_button, dialog.save_button):
            self.assertTrue(control.isVisible())
            self.assertLess(control.mapTo(dialog, control.rect().bottomRight()).y(), dialog.height())
        self.assertLessEqual(dialog.save_button.geometry().bottom(), dialog.height())
        dialog.view_select.setCurrentIndex(1)
        self.qt.processEvents()
        self.assertEqual(dialog.height(), 416)
        dialog.close()
        dialog.deleteLater()

    def test_appearance_preview_does_not_change_saved_settings(self):
        config = {}
        dialog = SettingsDialog(config, self.manager)
        self.assertEqual(dialog.opacity_slider.value(), 100)
        self.assertTrue(dialog.rounded_cb.isChecked())
        dialog.opacity_slider.setValue(70)
        dialog.rounded_cb.setChecked(False)
        self.assertEqual(dialog.get_values()["background_opacity"], 70)
        self.assertFalse(dialog.get_values()["rounded_corners"])
        self.assertEqual(dialog.preview_card.app_ref.config["background_opacity"], 70)
        self.assertEqual(config, {})
        dialog.reject()
        dialog.deleteLater()

    def test_compact_preview_uses_actual_card_size_without_stretching(self):
        from PyQt6.QtCore import QRect
        from unittest.mock import Mock
        dialog = SettingsDialog({}, self.manager)
        dialog._settings_screen = Mock()
        dialog._settings_screen.availableGeometry.return_value = QRect(0, 0, 1920, 1080)
        dialog.show()
        self.qt.processEvents()
        window_size = dialog.size()
        for index in (1, 0, 1):
            dialog.view_select.setCurrentIndex(index)
            self.qt.processEvents()
            self.assertEqual(dialog.size(), window_size)
            if index == 1:
                self.assertEqual((dialog.preview_card.width(), dialog.preview_card.height()), (404, 130))
                self.assertLess(dialog.preview_card.height(), dialog.preview_frame.height())
                self.assertGreater(dialog.preview_card.pos().y(), 0)
            else:
                self.assertGreater(dialog.preview_card.width(), 404)
        dialog.close()
        dialog.deleteLater()
