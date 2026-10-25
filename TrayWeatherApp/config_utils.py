# TrayWeatherApp module: config_utils.py

from datetime import datetime
from datetime import datetime, timezone, timedelta
from pathlib import Path
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QPixmap, QFont, QPainter, QLinearGradient, QColor
from PyQt6.QtWidgets import (    
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QTabWidget,
    QSystemTrayIcon, QMenu, QDialog, QFormLayout, QPushButton,
    QComboBox, QInputDialog, QCheckBox, QSpacerItem, QSizePolicy,
    QGraphicsDropShadowEffect, QTabBar, QToolButton
)
import json
import sys, json, requests, traceback, platform, ctypes, zipfile, io, re

# ---------- Paths ----------
def get_base_path() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

CONFIG_PATH = Path.home() / ".TrayWeatherApp" / "pyqt_tray_weather.json"
LOG_PATH = CONFIG_PATH.with_name("pyqt_tray_weather.log")
BASE_DIR = get_base_path()
PORTABLE_THEMES_DIR = BASE_DIR / "themes"
THEMES_DIR = CONFIG_PATH.parent / "themes"

DEFAULT_CONFIG = {
    "cities": ["New York"],
    "units": "imperial",
    "window_pos": [100, 100],
    "window_size": [760, 500],
    "view_mode": "normal",
    "debug": False,
    "time_format_24h": False,
    "theme": "System"
}


CONFIG_PATH = Path.home() / ".TrayWeatherApp" / "pyqt_tray_weather.json"

def load_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "cities": ["New York"],
        "units": "imperial",
        "window_pos": [100, 100],
        "window_size": [760, 500],
    "view_mode": "normal",
        "debug": False,
        "time_format_24h": False,
        "theme": "System"
    }

def save_config(cfg: dict):
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except Exception as e:
        with open(Path.home() / ".TrayWeatherApp" / "pyqt_tray_weather.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [ERROR] Failed to save config: {e}\n")

# ---------- Logging ----------
def log(msg, level="DEBUG"):
    try:
        debug_enabled = True
        if CONFIG_PATH.exists():
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            debug_enabled = cfg.get("debug", True)
        if not debug_enabled and level == "DEBUG":
            return
        line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [{level}] {msg}"
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ---------- Icons ----------
def create_tray_icon(emoji: str = "☀️") -> QIcon:
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setFont(QFont("Segoe UI Emoji", 48))
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, emoji)
    p.end()
    return QIcon(pix)

def format_tray_temperature(temperature):
    import math
    if (not isinstance(temperature, (int, float)) or isinstance(temperature, bool)
            or not math.isfinite(temperature)):
        return "—"
    return f"{round(temperature)}°"


def create_temperature_icon(temperature):
    """High-contrast temperature text sized for the tray, without emoji overlap."""
    from PyQt6.QtCore import QPointF
    from PyQt6.QtGui import QPainterPath, QPen, QFontMetricsF
    text = format_tray_temperature(temperature)
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    font = QFont("Segoe UI", weight=QFont.Weight.Bold)
    for size in range(46, 7, -1):
        font.setPixelSize(size)
        metrics = QFontMetricsF(font)
        if metrics.horizontalAdvance(text) <= 58:
            break
    path = QPainterPath()
    path.addText(QPointF(0, 0), font, text)
    bounds = path.boundingRect()
    path.translate(32 - bounds.center().x(), 32 - bounds.center().y())
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor("#14171C"), 3))
    painter.setBrush(QColor("#FFFFFF"))
    painter.drawPath(path)
    painter.end()
    return QIcon(pixmap)


def set_sun_icon(window):
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setFont(QFont("Segoe UI Emoji", 48))
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "☀️")
    painter.end()
    window.setWindowIcon(QIcon(pix))

# ---------- Blur ----------
def enable_windows_acrylic(widget):
    try:
        if platform.system() != "Windows":
            return
        hwnd = widget.winId().__int__()

        class ACCENTPOLICY(ctypes.Structure):
            _fields_ = [("AccentState", ctypes.c_int),
                        ("AccentFlags", ctypes.c_int),
                        ("GradientColor", ctypes.c_uint32),
                        ("AnimationId", ctypes.c_int)]

        class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
            _fields_ = [("Attribute", ctypes.c_int),
                        ("Data", ctypes.c_void_p),
                        ("SizeOfData", ctypes.c_size_t)]

        WCA_ACCENT_POLICY = 19
        ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
        gradient_color = 0xCC222222

        accent = ACCENTPOLICY()
        accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
        accent.GradientColor = gradient_color
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = WCA_ACCENT_POLICY
        data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p)
        data.SizeOfData = ctypes.sizeof(accent)

        ctypes.windll.user32.SetWindowCompositionAttribute(ctypes.c_void_p(hwnd), ctypes.byref(data))
    except Exception as e:
        log(f"Acrylic blur unavailable: {e}")
