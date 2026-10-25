# TrayWeatherApp module: ui_components.py

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QWidget,
    QDialog,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QComboBox,
    QCheckBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem
)
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from TrayWeatherApp.config_utils import log, set_sun_icon, enable_windows_acrylic
from TrayWeatherApp.theme import ThemeManager

# ---------- Glass Card ----------
class GlassCard(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent; border: none;")
        self.app_ref = app_ref
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.radius = 22
        self.bg_color = QColor(20,22,30,150)  # will be replaced in apply_theme_to_card
        self.icon_lbl = QLabel("☀️"); self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setFont(QFont("Segoe UI Emoji", 120))
        glow = QGraphicsDropShadowEffect(self.icon_lbl); glow.setBlurRadius(30)
        glow.setColor(QColor(255, 200, 120, 90)); glow.setOffset(0,0)
        self.icon_lbl.setGraphicsEffect(glow)
        self.city_lbl = QLabel("City")
        self.city_lbl.setWordWrap(True)
        self.city_lbl.setTextFormat(Qt.TextFormat.PlainText)
        self.time_lbl = QLabel("🕒 --:--")
        city_row = QVBoxLayout(); city_row.setSpacing(4)
        city_row.addWidget(self.city_lbl); city_row.addWidget(self.time_lbl)
        self.temp_lbl = QLabel("-°")
        self.desc_lbl = QLabel("-")
        self.more_lbl = QLabel("-"); self.more_lbl.setWordWrap(True)
        self.more_lbl.setTextFormat(Qt.TextFormat.RichText)
        right = QVBoxLayout(); right.addLayout(city_row); right.addWidget(self.temp_lbl)
        right.addWidget(self.desc_lbl); right.addWidget(self.more_lbl)
        self.status_lbl = QLabel("Waiting for weather")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setTextFormat(Qt.TextFormat.PlainText)
        right.addWidget(self.status_lbl)
        right.addStretch(1)
        row = QHBoxLayout(self); row.setContentsMargins(26,26,26,26); row.setSpacing(26)
        row.addWidget(self.icon_lbl); row.addLayout(right,1)
        self.icon_lbl.setFixedWidth(150)
        self.city_lbl.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.time_lbl.setFont(QFont("Segoe UI", 11))
        self.desc_lbl.setFont(QFont("Segoe UI", 13))
        self.more_lbl.setFont(QFont("Segoe UI", 11))
        self.apply_theme_to_card()

    def apply_theme_to_card(self):
        t = self.app_ref.theme
        # colors
        glass = t.value("glass_card_color", "rgba(20,22,30,150)")
        border = t.value("card_border_color", "rgba(255,255,255,25)")
        text_primary = t.value("text_primary", "#E6E8EE")
        text_muted = t.value("text_muted", "#9EA3B8")
        text_desc = t.value("text_desc", "#C5C9D3")
        text_more = t.value("text_more", "#A8AFC2")
        temp_color = t.value("temp_color", "#FFD18A")
        high_color = t.value("high_color", "#FFB347")
        low_color  = t.value("low_color",  "#7DD3FC")
        humid_color= t.value("humid_color","#7DD3FC")
        wind_color = t.value("wind_color", "#C4B5FD")
        glow_color = t.value("accent_glow", "#FFC878")

        self.bg_color = ThemeManager.parse_color(glass, "rgba(20,22,30,150)")
        self._border_color = ThemeManager.parse_color(border, "rgba(255,255,255,25)")

        self.city_lbl.setStyleSheet(f"color:{text_primary};")
        self.city_lbl.setFont(QFont("Segoe UI",20,QFont.Weight.Bold))
        self.status_lbl.setStyleSheet(f"color:{text_muted}; font-size:11px;")
        self.time_lbl.setStyleSheet(f"color:{text_muted};")
        self.temp_lbl.setStyleSheet(f"color:{temp_color};")
        self.temp_lbl.setFont(QFont("Segoe UI",38))
        self.desc_lbl.setStyleSheet(f"color:{text_desc};")
        self.more_lbl.setStyleSheet(f"color:{text_more};")

        glow = self.icon_lbl.graphicsEffect()
        if isinstance(glow, QGraphicsDropShadowEffect):
            glow.setColor(ThemeManager.parse_color(glow_color, "#FFC878"))

        self._colors = {
            "temp": temp_color,
            "high": high_color,
            "low": low_color,
            "humid": humid_color,
            "wind": wind_color,
        }

        self.update()
        self.repaint()

    def themed_detail_html(self, feels, high, low, humid, wind, units_t, units_w):
        c = self._colors
        return (
            "<table cellspacing='6' cellpadding='0'>"
            f"<tr><td colspan='2'>Feels like: <span style='color:{c['temp']}'>{feels}°{units_t}</span></td></tr>"
            f"<tr><td width='170'>High: <span style='color:{c['high']}'>{high}°{units_t}</span></td>"
            f"<td>Low: <span style='color:{c['low']}'>{low}°{units_t}</span></td></tr>"
            f"<tr><td width='170'>Humidity: <span style='color:{c['humid']}'>{humid}%</span></td>"
            f"<td>Wind: <span style='color:{c['wind']}'>{wind}&nbsp;{units_w}</span></td></tr>"
            "</table>"
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.apply_responsive_layout()

    def apply_responsive_layout(self):
        # Keep text sizes stable. Give narrow windows the full width for text.
        self.icon_lbl.setVisible(self.width() >= 620)
        icon_size = max(64, min(110, int(self.height() * 0.26)))
        self.icon_lbl.setFont(QFont("Segoe UI Emoji", icon_size))


    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        mode_clear = getattr(QPainter, "CompositionMode_Clear", None) \
            or getattr(getattr(QPainter, "CompositionMode", None), "Clear", None)
        if mode_clear:
            p.setCompositionMode(mode_clear)
            p.fillRect(self.rect(), Qt.GlobalColor.transparent)

        mode_sourceover = getattr(QPainter, "CompositionMode_SourceOver", None) \
            or getattr(getattr(QPainter, "CompositionMode", None), "SourceOver", None)
        if mode_sourceover:
            p.setCompositionMode(mode_sourceover)

        r = self.rect().adjusted(0, 0, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(QRectF(r), 16, 16)

        p.fillPath(path, self.bg_color)
        p.setPen(QPen(self._border_color, 0.8))
        p.drawPath(path)

