# TrayWeatherApp module: settings.py

from datetime import datetime, timezone, timedelta
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QPixmap, QFont, QIcon, QPainter, QLinearGradient, QColor,
    QPainterPath
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QInputDialog, QToolButton, QTabBar,
    QLabel, QSizePolicy, QSpacerItem, QDialog, QFormLayout, QComboBox,
    QCheckBox, QPushButton, QHBoxLayout
)
from TrayWeatherApp.config_utils import set_sun_icon, create_tray_icon, enable_windows_acrylic, log

# ---------- Settings Dialog ----------
class SettingsDialog(QDialog):
    def __init__(self, config, theme_manager: "ThemeManager"):
        super().__init__()
        self.setWindowTitle("Settings")
        set_sun_icon(self)
        self.resize(320, 180)
        self.theme_manager = theme_manager

        self.units_input = QComboBox()
        self.units_input.addItems(["metric", "imperial"])
        self.units_input.setCurrentText(config.get("units", "metric"))

        self.time_cb = QCheckBox("Use 24-hour clock")
        self.time_cb.setChecked(config.get("time_format_24h", True))

        self.debug_cb = QCheckBox("Enable debug logging")
        self.debug_cb.setChecked(config.get("debug", True))

        self.theme_select = QComboBox()
        names = self.theme_manager.list_themes()
        if not names:
            self.theme_select.addItem("(no themes found)")
            self.theme_select.setEnabled(False)
        else:
            self.theme_select.addItems(names)
            current = config.get("theme", names[0])
            if current in names:
                self.theme_select.setCurrentText(current)

        form = QFormLayout()
        form.addRow("Units", self.units_input)
        form.addRow("Theme", self.theme_select)
        form.addRow(self.time_cb)
        form.addRow(self.debug_cb)

        save, cancel = QPushButton("Save"), QPushButton("Cancel")
        save.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(cancel)
        btns.addWidget(save)
        lay = QVBoxLayout()
        lay.addLayout(form)
        lay.addLayout(btns)
        self.setLayout(lay)
        self.apply_theme_to_dialog()

    def apply_theme_to_dialog(self):
        t = self.theme_manager
        bg = t.value("glass_card_color", "rgba(20,22,30,150)")
        text = t.value("text_primary", "#E6E8EE")
        accent = t.value("link_color", "#7DD3FC")

        bright_theme = any(name in t.value("name", "").lower() for name in ["light", "beach", "sand", "day"])
        if bright_theme:
            bg = "rgba(255,255,255,0.95)"
            text = "#1B263B"
            accent = "#0D47A1"

        qss = f"""
        QDialog {{
            background-color: {bg};
            color: {text};
            font-family: "Segoe UI";
        }}
        QLabel, QCheckBox {{
            color: {text};
        }}
        QComboBox, QLineEdit {{
            background: {'rgba(255,255,255,0.9)' if bright_theme else 'rgba(255,255,255,0.05)'};
            color: {text};
            border: 1px solid {'rgba(0,0,0,0.2)' if bright_theme else 'rgba(255,255,255,0.15)'};
            border-radius: 6px;
            padding: 4px 8px;
        }}
        QComboBox QAbstractItemView {{
            background: {'white' if bright_theme else '#232323'};
            color: {text};
            selection-background-color: {'#E0E0E0' if bright_theme else '#444'};
        }}
        QPushButton {{
            background-color: {accent};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 6px 12px;
        }}
        QPushButton:hover {{
            background-color: {accent}CC;
        }}
        QPushButton:pressed {{
            background-color: {accent}99;
        }}
        """
        self.setStyleSheet(qss)

    def get_values(self):
        return {
            "units": self.units_input.currentText(),
            "time_format_24h": self.time_cb.isChecked(),
            "debug": self.debug_cb.isChecked(),
            "theme": self.theme_select.currentText() if self.theme_select.isEnabled() else None
        }
