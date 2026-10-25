"""Settings with an isolated theme preview; only Save changes the live theme."""
from types import SimpleNamespace

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QDesktopServices, QCursor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QCheckBox,
    QPushButton, QLabel, QFileDialog, QMessageBox, QFrame,
    QWidget, QApplication, QSizePolicy,
)
from TrayWeatherApp.config_utils import set_sun_icon
from TrayWeatherApp.theme import ThemeManager, ThemeError
from TrayWeatherApp.ui_components import GlassCard


class SettingsDialog(QDialog):
    def __init__(self, config, theme_manager):
        super().__init__()
        self.setWindowTitle("Settings")
        set_sun_icon(self)
        self._settings_screen = QApplication.screenAt(QCursor.pos()) or self.screen()
        self.theme_manager = theme_manager
        self.preview_theme = ThemeManager(theme_manager.custom_dir,
                                          theme_manager.builtin_dir,
                                          theme_manager.legacy_dirs)
        self.units_input = QComboBox()
        self.units_input.addItems(["metric", "imperial"])
        self.units_input.setCurrentText(config.get("units", "imperial"))
        self.view_select = QComboBox()
        self.view_select.addItem("Normal", "normal")
        self.view_select.addItem("Compact", "compact")
        self.view_select.setCurrentIndex(1 if config.get("view_mode") == "compact" else 0)
        self.tray_select = QComboBox()
        self.tray_select.addItem("Weather icon", "icon")
        self.tray_select.addItem("Temperature only", "temperature")
        self.tray_select.setCurrentIndex(1 if config.get("tray_display") == "temperature" else 0)
        self.time_cb = QCheckBox("Use 24-hour clock")
        self.time_cb.setChecked(config.get("time_format_24h", False))
        self.debug_cb = QCheckBox("Enable debug logging")
        self.debug_cb.setChecked(config.get("debug", False))
        self.theme_select = QComboBox()
        self.theme_select.addItems(theme_manager.list_themes())
        current = theme_manager.current_name
        self.theme_select.setCurrentText(current)
        form = QFormLayout()
        form.addRow("Units", self.units_input)
        form.addRow("Theme", self.theme_select)
        form.addRow("View", self.view_select)
        form.addRow("Tray display", self.tray_select)
        form.addRow(self.time_cb)
        form.addRow(self.debug_cb)
        outer = QVBoxLayout(self)
        content = QWidget()
        content.setObjectName("SettingsContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(content, 1)
        layout.addLayout(form)
        if theme_manager.last_error:
            warning = QLabel(f"Saved theme unavailable; using Dark. {theme_manager.last_error}")
            warning.setWordWrap(True)
            layout.addWidget(warning)

        tools = QHBoxLayout()
        for label, callback in [("Import Theme…", self.import_theme),
                                 ("Export Theme…", self.export_theme),
                                 ("Open Themes Folder", self.open_themes_folder)]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            tools.addWidget(button)
        layout.addLayout(tools)
        self.source_label = QLabel()
        self.source_label.setWordWrap(True)
        layout.addWidget(self.source_label)
        self.preview_caption = QLabel("Preview — Save applies this theme to the app.")
        layout.addWidget(self.preview_caption)
        self.preview_frame = QFrame()
        self.preview_frame.setObjectName("ThemePreview")
        self.preview_frame.setFixedHeight(340)
        preview_layout = QVBoxLayout(self.preview_frame)
        self.preview_card = GlassCard(SimpleNamespace(theme=self.preview_theme))
        self.preview_card.city_lbl.setText("New York")
        self.preview_card.time_lbl.setText("🕒 10:30 AM")
        self.preview_card.desc_lbl.setText("Partly cloudy")
        self.preview_card.status_lbl.setText("Up to date · Updated just now")
        preview_layout.addWidget(self.preview_card)
        layout.addWidget(self.preview_frame)
        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)
        buttons = QHBoxLayout()
        self.about_button = QPushButton("About")
        self.about_button.clicked.connect(self.show_about)
        buttons.addWidget(self.about_button)
        buttons.addStretch()
        self.cancel_button = QPushButton("Cancel")
        self.save_button = QPushButton("Save")
        self.cancel_button.clicked.connect(self.reject)
        self.save_button.clicked.connect(self.accept)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.save_button)
        outer.addLayout(buttons)
        self.theme_select.currentTextChanged.connect(self.update_preview)
        self.units_input.currentTextChanged.connect(self.update_preview)
        self.time_cb.toggled.connect(self.update_preview)
        self.view_select.currentIndexChanged.connect(self.update_preview)
        self.update_preview()
        self.fit_to_screen()

    def show_about(self):
        from ._version import __version__
        QMessageBox.about(
            self, "About TrayWeatherApp",
            f"<h3>TrayWeatherApp {__version__}</h3>"
            "<p>Created by evil1dwk</p><p>Weather data from Open-Meteo.</p>"
            "<p><a href='https://github.com/evil1dwk/TrayWeatherApp'>Project</a>"
            " · <a href='https://github.com/evil1dwk/TrayWeatherApp/issues'>Report an issue</a></p>")

    def fit_to_screen(self):
        available = self._settings_screen.availableGeometry()
        # Leave space for the native title bar and desktop panels.
        height = max(1, min(760, available.height() - 64))
        # Preserve access to every setting and action on short displays. The
        # decorative preview is optional; the dialog never needs scrollbars.
        show_preview = height >= 700
        self.preview_caption.setVisible(show_preview)
        self.preview_frame.setVisible(show_preview)
        self.setFixedSize(max(1, min(680, available.width() - 32)), height)

    def showEvent(self, event):
        super().showEvent(event)
        self.fit_to_screen()
        available = self._settings_screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    def update_preview(self, *_):
        name = self.theme_select.currentText()
        try:
            self.preview_theme.load_theme(name)
        except (ThemeError, FileNotFoundError) as exc:
            self.error_label.setText(f"Cannot use this theme: {exc}")
            self.save_button.setEnabled(False)
            return
        self.error_label.clear()
        self.save_button.setEnabled(True)
        background = self.preview_theme.value("background_gradient")[0]
        self.setStyleSheet(self.preview_theme.stylesheet() +
                          f"QWidget#SettingsContent {{ background: {background}; }}")
        self.preview_card.apply_theme_to_card()
        mode = self.view_select.currentData()
        self.preview_card.set_view_mode(mode)
        if mode == "compact":
            # Match the real compact card instead of stretching it to fill
            # the fixed-height preview area reserved for the Normal layout.
            self.preview_card.setFixedSize(404, 130)
            self.preview_frame.layout().setAlignment(self.preview_card, Qt.AlignmentFlag.AlignCenter)
        else:
            self.preview_card.setMinimumSize(0, 0)
            self.preview_card.setMaximumSize(16777215, 16777215)
            self.preview_frame.layout().setAlignment(self.preview_card, Qt.AlignmentFlag(0))
        self.preview_card.updateGeometry()
        metric = self.units_input.currentText() == "metric"
        temperature, wind = ("C", "km/h") if metric else ("F", "mph")
        self.preview_card.temp_lbl.setText("21.0°C" if metric else "69.8°F")
        self.preview_card.time_lbl.setText("🕒 10:30" if self.time_cb.isChecked() else "🕒 10:30 AM")
        self.preview_card.more_lbl.setText(self.preview_card.themed_detail_html(
            21 if metric else 70, 24 if metric else 75, 16 if metric else 61,
            55, 12 if metric else 7, temperature, wind))
        gradient = self.preview_theme.value("background_gradient")
        colors = [self.preview_theme.parse_color(c).name() for c in gradient]
        self.preview_frame.setStyleSheet(
            f"QFrame#ThemePreview {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {colors[0]},stop:1 {colors[1]}); }}")
        catalog = self.theme_manager.catalog()
        path = catalog.get(name)
        source = ("Follows the operating system's Light/Dark preference." if name == "System"
                  else "Built-in theme" if path and path.parent == self.theme_manager.builtin_dir
                  else "Custom / legacy theme")
        self.source_label.setText(source)
        self.preview_card.sync_compact()

    def accept(self):
        # Revalidate in case the file was edited while Settings was open.
        self.update_preview()
        if self.save_button.isEnabled():
            super().accept()

    def import_theme(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Theme", "", "Themes (*.json *.zip)")
        if not path:
            return
        try:
            name = self.theme_manager.import_theme(path)
        except (ThemeError, OSError) as exc:
            QMessageBox.warning(self, "Theme import failed", str(exc))
            return
        self.theme_select.clear()
        self.theme_select.addItems(self.theme_manager.list_themes())
        self.theme_select.setCurrentText(name)

    def export_theme(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Theme", "theme.json", "JSON theme (*.json)")
        if not path:
            return
        try:
            self.theme_manager.export_theme(self.theme_select.currentText(), path)
        except (ThemeError, FileNotFoundError, OSError) as exc:
            QMessageBox.warning(self, "Theme export failed", str(exc))

    def open_themes_folder(self):
        self.theme_manager.custom_dir.mkdir(parents=True, exist_ok=True)
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.theme_manager.custom_dir))):
            QMessageBox.information(self, "Themes Folder", str(self.theme_manager.custom_dir))

    def get_values(self):
        return {
            "units": self.units_input.currentText(),
            "view_mode": self.view_select.currentData(),
            "tray_display": self.tray_select.currentData(),
            "time_format_24h": self.time_cb.isChecked(),
            "debug": self.debug_cb.isChecked(),
            "theme": self.theme_select.currentText(),
        }
