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
    QSpacerItem, QToolButton
)
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from TrayWeatherApp.config_utils import log, set_sun_icon, enable_windows_acrylic
from TrayWeatherApp.theme import ThemeManager
from TrayWeatherApp.forecast import ForecastPanel

# ---------- Glass Card ----------
class GlassCard(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent; border: none;")
        self.app_ref = app_ref
        self.view_mode = getattr(app_ref, "config", {}).get("view_mode", "normal")
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
        self.normal_panel = QWidget()
        row = QHBoxLayout(self.normal_panel); row.setContentsMargins(26,26,26,26); row.setSpacing(26)
        row.addWidget(self.icon_lbl); row.addLayout(right,1)
        self.icon_lbl.setFixedWidth(150)
        self.city_lbl.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.time_lbl.setFont(QFont("Segoe UI", 11))
        self.desc_lbl.setFont(QFont("Segoe UI", 13))
        self.more_lbl.setFont(QFont("Segoe UI", 11))
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.normal_panel)
        self.compact_panel = QWidget()
        compact = QVBoxLayout(self.compact_panel)
        compact.setContentsMargins(12, 10, 12, 8)
        compact.setSpacing(2)
        main_row = QHBoxLayout()
        main_row.setSpacing(12)
        self.compact_icon = QLabel("☀️")
        self.compact_icon.setFixedWidth(54)
        self.compact_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_row.addWidget(self.compact_icon)
        text = QVBoxLayout()
        text.setSpacing(1)
        self.compact_city = QLabel("City")
        self.compact_city.setTextFormat(Qt.TextFormat.PlainText)
        self.compact_city.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        text.addWidget(self.compact_city)
        reading = QHBoxLayout()
        reading.setSpacing(10)
        self.compact_temp = QLabel("-°")
        self.compact_desc = QLabel("-")
        self.compact_desc.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        reading.addWidget(self.compact_temp)
        reading.addWidget(self.compact_desc, 1)
        text.addLayout(reading)
        main_row.addLayout(text, 1)
        compact.addLayout(main_row)
        self.compact_summary = QLabel("Feels —  ·  High — / Low —")
        self.compact_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        compact.addWidget(self.compact_summary)
        footer = QHBoxLayout()
        self.compact_status = QLabel("Waiting for weather")
        self.compact_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        footer.addWidget(self.compact_status, 1)
        self.settings_button = QToolButton()
        self.settings_button.setText("⚙")
        self.settings_button.setToolTip("Settings")
        self.settings_button.setFixedSize(24, 24)
        callback = getattr(app_ref, "open_settings", None)
        if callback:
            self.settings_button.clicked.connect(callback)
        else:
            self.settings_button.setEnabled(False)
        footer.addStretch(1)
        footer.addWidget(self.settings_button)
        self.normal_settings_button = QToolButton()
        self.normal_settings_button.setText("⚙")
        self.normal_settings_button.setToolTip("Settings")
        self.normal_settings_button.setFixedSize(24, 24)
        if callback:
            self.normal_settings_button.clicked.connect(callback)
        else:
            self.normal_settings_button.setEnabled(False)
        normal_footer = QHBoxLayout()
        normal_footer.addStretch(1)
        normal_footer.addWidget(self.normal_settings_button)
        right.addLayout(normal_footer)
        compact.addLayout(footer)
        outer.addWidget(self.compact_panel)
        self.forecast_panel = ForecastPanel(app_ref)
        outer.addWidget(self.forecast_panel)
        self.forecast_mode = False
        self._compact_summary = "Feels —  ·  High — / Low —"
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

        for label, color in [(self.compact_city, text_primary), (self.compact_temp, temp_color),
                             (self.compact_desc, text_desc), (self.compact_summary, text_more),
                             (self.compact_status, text_muted)]:
            label.setStyleSheet(f"color:{color}; background:transparent;")
        self.set_view_mode(self.view_mode)
        self.update()
        self.repaint()

    def themed_detail_html(self, feels, high, low, humid, wind, units_t, units_w):
        def short(value):
            return f"{value:.0f}" if isinstance(value, (int, float)) else "—"
        self._compact_summary = f"Feels {short(feels)}°  ·  High {short(high)}° / Low {short(low)}°"
        self.compact_summary.setText(self._compact_summary)
        self.compact_summary.setToolTip(f"Humidity: {humid}% · Wind: {wind} {units_w}")
        c = self._colors
        column_width = 130 if self.view_mode == "compact" else 170
        return (
            "<table cellspacing='6' cellpadding='0'>"
            f"<tr><td colspan='2'>Feels like: <span style='color:{c['temp']}'>{feels}°{units_t}</span></td></tr>"
            f"<tr><td width='{column_width}'>High: <span style='color:{c['high']}'>{high}°{units_t}</span></td>"
            f"<td>Low: <span style='color:{c['low']}'>{low}°{units_t}</span></td></tr>"
            f"<tr><td width='{column_width}'>Humidity: <span style='color:{c['humid']}'>{humid}%</span></td>"
            f"<td>Wind: <span style='color:{c['wind']}'>{wind}&nbsp;{units_w}</span></td></tr>"
            "</table>"
        )

    def set_view_mode(self, mode):
        self.view_mode = "compact" if mode == "compact" else "normal"
        compact = self.view_mode == "compact"
        self.normal_panel.layout().setContentsMargins(22, 22, 22, 22)
        self.normal_panel.layout().setSpacing(18)
        self.status_lbl.setVisible(False)
        self.compact_status.setVisible(False)
        self.normal_panel.setVisible(not compact and not self.forecast_mode)
        self.compact_panel.setVisible(compact and not self.forecast_mode)
        self.forecast_panel.setVisible(self.forecast_mode)
        self.forecast_panel.set_view_mode(self.view_mode)
        self.icon_lbl.setVisible(True)
        self.icon_lbl.setFixedWidth(90 if compact else 150)
        self.icon_lbl.setFont(QFont("Segoe UI Emoji", 62 if compact else 100))
        self.city_lbl.setFont(QFont("Segoe UI", 16 if compact else 20, QFont.Weight.Bold))
        self.time_lbl.setFont(QFont("Segoe UI", 10 if compact else 11))
        self.temp_lbl.setFont(QFont("Segoe UI", 30 if compact else 38))
        self.desc_lbl.setFont(QFont("Segoe UI", 11 if compact else 13))
        self.more_lbl.setFont(QFont("Segoe UI", 10 if compact else 11))
        self.status_lbl.setFont(QFont("Segoe UI", 10))
        self.compact_icon.setFont(QFont("Segoe UI Emoji", 36))
        self.compact_city.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.compact_temp.setFont(QFont("Segoe UI", 29))
        self.compact_desc.setFont(QFont("Segoe UI", 10))
        self.compact_summary.setFont(QFont("Segoe UI", 9))
        self.compact_status.setFont(QFont("Segoe UI", 9))
        self.sync_compact()

    def set_forecast_mode(self, enabled):
        self.forecast_mode = enabled
        self.set_view_mode(self.view_mode)

    def sync_compact(self):
        self.compact_city.setText(self.city_lbl.text())
        self.compact_city.setToolTip(self.city_lbl.toolTip())
        self.compact_temp.setText(self.temp_lbl.text())
        self.compact_desc.setText(self.desc_lbl.text())
        self.compact_desc.setToolTip(self.desc_lbl.text())
        self.compact_icon.setText(self.icon_lbl.text())
        self.compact_icon.setToolTip(self.compact_summary.toolTip() + "\n" + self.time_lbl.text())
        self.compact_summary.setText(self._compact_summary)
        # Freshness owns the compact status; layout updates must not replace
        # its short text with the Normal-view status.

    def apply_responsive_layout(self):
        # Kept for callers refreshing an existing card; never hide its icon.
        self.set_view_mode(self.view_mode)

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

