"""Daily forecast presentation shared by Normal and Compact cards."""
from datetime import date
import math

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QToolButton, QSizePolicy


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def parse_daily(daily, map_code):
    if not isinstance(daily, dict):
        return []
    dates = daily.get("time", [])
    if not isinstance(dates, list):
        return []
    result = []
    def at(key, index):
        values = daily.get(key, [])
        return values[index] if isinstance(values, list) and index < len(values) else None
    for index, raw in enumerate(dates[:5]):
        try:
            day = date.fromisoformat(raw)
        except (TypeError, ValueError):
            continue
        high, low = at("temperature_2m_max", index), at("temperature_2m_min", index)
        probability = at("precipitation_probability_max", index)
        code = at("weather_code", index)
        description, icon = map_code(code if isinstance(code, int) else None)
        result.append({"date": day.isoformat(), "high": high if number(high) else None,
                       "low": low if number(low) else None, "description": description, "icon": icon,
                       "precipitation_probability": probability if number(probability) and 0 <= probability <= 100 else None})
    return result


class ForecastPanel(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self.mode = "normal"
        self.info = {}
        self.box = QVBoxLayout(self)
        self.box.setSpacing(4)
        self.city = QLabel("City")
        self.city.setTextFormat(Qt.TextFormat.PlainText)
        self.city.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.box.addWidget(self.city)
        self.subtitle = QLabel("5-day forecast")
        self.box.addWidget(self.subtitle)
        self.message = QLabel("Forecast unavailable. Refresh weather to download it.")
        self.message.setWordWrap(True)
        self.box.addWidget(self.message)
        columns = QHBoxLayout()
        columns.setSpacing(4)
        self.columns = []
        for _ in range(5):
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(2, 0, 2, 0)
            layout.setSpacing(2)
            labels = [QLabel() for _ in range(5)]
            for label in labels:
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setTextFormat(Qt.TextFormat.PlainText)
                layout.addWidget(label)
            columns.addWidget(widget, 1)
            self.columns.append((widget, labels))
        self.box.addLayout(columns, 1)
        footer = QHBoxLayout()
        footer.addStretch()
        self.settings = QToolButton()
        self.settings.setText("⚙")
        self.settings.setToolTip("Settings")
        self.settings.setFixedSize(20, 20)
        callback = getattr(app_ref, "open_settings", None)
        if callback:
            self.settings.clicked.connect(callback)
        else:
            self.settings.setEnabled(False)
        footer.addWidget(self.settings)
        self.box.addLayout(footer)
        self.render()

    def set_weather(self, info):
        self.info = info
        self.render()

    def set_view_mode(self, mode):
        self.mode = mode
        self.render()

    def render(self):
        compact = self.mode == "compact"
        theme = self.app_ref.theme
        self.box.setContentsMargins(10 if compact else 22, 3 if compact else 18,
                                   10 if compact else 22, 2 if compact else 12)
        self.box.setSpacing(2 if compact else 4)
        self.settings.setFixedSize(16, 16) if compact else self.settings.setFixedSize(20, 20)
        location = self.info.get("location") or {}
        full = self.info.get("city", "City")
        self.city.setText(location.get("name") or full.split(",")[0])
        self.city.setToolTip(full)
        self.city.setFont(QFont("Segoe UI", 11 if compact else 20, QFont.Weight.Bold))
        self.city.setStyleSheet(f"color:{theme.value('text_primary')}; background:transparent;")
        self.subtitle.setVisible(not compact)
        self.subtitle.setStyleSheet(f"color:{theme.value('text_muted')}; background:transparent;")
        days = self.info.get("forecast", [])
        days = days if isinstance(days, list) else []
        self.message.setVisible(not days)
        self.message.setFont(QFont("Segoe UI", 9 if compact else 11))
        self.message.setStyleSheet(f"color:{theme.value('text_muted')}; background:transparent;")
        for index, (widget, labels) in enumerate(self.columns):
            visible = index < len(days) and index < (3 if compact else 5)
            widget.setVisible(visible)
            if not visible:
                continue
            day = days[index]
            if not isinstance(day, dict):
                widget.hide()
                continue
            try:
                parsed = date.fromisoformat(day["date"])
            except (TypeError, ValueError, KeyError):
                widget.hide()
                continue
            widget.layout().setSpacing(0 if compact else 2)
            heading, icon, high, low, probability = labels
            heading.setText(parsed.strftime("%a"))
            icon.setText(day.get("icon", "🌍"))
            high.setText(f"{day['high']:.0f}°" if number(day.get("high")) else "—")
            low.setText(f"{day['low']:.0f}°" if number(day.get("low")) else "—")
            rain = day.get("precipitation_probability")
            probability.setText(f"{rain:.0f}% precip." if number(rain) else "—")
            probability.setVisible(not compact)
            tooltip = (f"{parsed.strftime('%A, %B %d')} · {day.get('description', 'Unknown')}\n"
                       f"Chance of precipitation: {rain:.0f}%" if number(rain) else
                       f"{parsed.isoformat()} · {day.get('description', 'Unknown')}\nPrecipitation chance unavailable")
            widget.setToolTip(tooltip)
            for label, color, size in [
                (heading, "text_primary", 9 if compact else 13),
                (icon, "text_primary", 16 if compact else 36),
                (high, "high_color", 12 if compact else 22),
                (low, "low_color", 10 if compact else 18),
                (probability, "text_muted", 9 if compact else 11),
            ]:
                label.setStyleSheet(f"color:{theme.value(color)}; background:transparent;")
                label.setFont(QFont("Segoe UI Emoji" if label is icon else "Segoe UI", size))
                label.setToolTip(tooltip)
