# TrayWeatherApp module: weather.py

from PyQt6.QtCore import Qt
from datetime import datetime, timezone, timedelta
from PyQt6.QtCore import Qt, QTimer, QSignalBlocker, QEvent
from PyQt6.QtGui import (
    QPixmap, QFont, QIcon, QPainter, QLinearGradient, QColor,
    QPainterPath, QFontMetrics
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QInputDialog, QToolButton, QTabBar,
    QLabel, QSizePolicy, QSpacerItem, QDialog, QFormLayout, QComboBox,
    QCheckBox, QPushButton, QHBoxLayout
)

from TrayWeatherApp.config_utils import set_sun_icon, create_tray_icon, enable_windows_acrylic, log, create_temperature_icon
from TrayWeatherApp.ui_components import GlassCard
from TrayWeatherApp.city_search import CitySearchDialog
from TrayWeatherApp.workers import location_label
from TrayWeatherApp.weather_cache import parse_timestamp

# ---------- Weather Window ----------
class WeatherWindow(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self.city_tabs = {}
        self.setWindowTitle("TrayWeatherApp")
        set_sun_icon(self)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self._drag_offset = None
        self.installEventFilter(self)
        self.move(*app_ref.config.get("window_pos", [100, 100]))
        enable_windows_acrylic(self)

        self.tabs = QTabWidget()
        self.tabs.setMovable(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabBar().tabMoved.connect(self.tabs_reordered)
        self.tabs.tabCloseRequested.connect(self.remove_tab)
        self.tabs.currentChanged.connect(self.check_fake_tab)
        self.tabs.tabBarClicked.connect(self.click_tab)
        self.tabs.currentChanged.connect(self.refresh_footer)
        self.apply_theme_to_tabs()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(0)
        lay.addWidget(self.tabs)

        # credit label
        self.credit_lbl = QLabel(
            "Powered by <a href='https://open-meteo.com/'>Open-Meteo</a>"
        )
        self.credit_lbl.setOpenExternalLinks(True)
        self.credit_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.apply_theme_to_credit()
        self.footer_status = QLabel("Waiting for weather")
        self.footer_status.setTextFormat(Qt.TextFormat.PlainText)
        self.footer_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(12)
        footer.addWidget(self.footer_status, 1)
        footer.addWidget(self.credit_lbl)
        lay.addLayout(footer)

        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(False)
        self.apply_view_mode()
        self.refresh_footer()

    def apply_view_mode(self):
        mode = self.app_ref.config.get("view_mode", "normal")
        self.layout().setContentsMargins(10, 8, 10, 10) if mode == "compact" else self.layout().setContentsMargins(18, 18, 18, 18)
        # Let the old fixed-size constraints go before changing child visibility.
        # Otherwise Windows can apply the old Normal layout's minimum height
        # during its native resize, leaving a tall Compact window until dragged.
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        for city, data in self.city_tabs.items():
            data["card"].set_view_mode(mode)
            if "info" in data:
                self.update_city_tab(city, data["info"])
        self.settle_view_size()
        # Settle again after pending layout requests and the Settings dialog's
        # close event. Read the current mode so rapid switches cannot restore
        # an obsolete size.
        QTimer.singleShot(0, self.settle_view_size)

    def settle_view_size(self):
        for widget in reversed(self.findChildren(QWidget)):
            layout = widget.layout()
            if layout:
                layout.invalidate()
                layout.activate()
            widget.updateGeometry()
        self.layout().invalidate()
        self.layout().activate()
        size = (440, 240) if self.app_ref.config.get("view_mode") == "compact" else (760, 500)
        self.setFixedSize(*size)
        self.layout().activate()
        self.refresh_footer()
        self.update()

    def refresh_footer(self, *_):
        if not hasattr(self, "footer_status"):
            return
        selected = self.tabs.currentWidget()
        data = next((data for data in self.city_tabs.values()
                     if data["container"] is selected), None)
        compact = self.app_ref.config.get("view_mode") == "compact"
        if data:
            card = data["card"]
            label = card.compact_status if compact else card.status_lbl
            text = label.text()
            tooltip = card.status_lbl.text()
            error = data.get("error", "")
            if error:
                tooltip += " · " + error
        else:
            text, tooltip = "No city selected", ""
        color = self.app_ref.theme.value("text_muted", "#9EA3B8")
        self.footer_status.setStyleSheet(f"color:{color}; font-size:11px; margin-top:4px; background:transparent;")
        footer_font = QFont("Segoe UI")
        footer_font.setPixelSize(11)
        self.footer_status.setFont(footer_font)
        self.credit_lbl.setFont(footer_font)
        # Rich-text QLabel size hints can retain the Windows system font's
        # width. Measure its known plain text with the same explicit font.
        metrics = QFontMetrics(footer_font)
        credit_width = metrics.horizontalAdvance("Powered by Open-Meteo") + 4
        self.credit_lbl.setFixedWidth(credit_width)
        self.footer_status.ensurePolished()
        self.credit_lbl.ensurePolished()
        margins = self.layout().contentsMargins()
        available = max(0, self.width() - margins.left() - margins.right()
                        - credit_width - 12)
        self.footer_status.setText(metrics.elidedText(
            text, Qt.TextElideMode.ElideRight, available))
        self.footer_status.setToolTip(tooltip)

    def apply_theme_to_credit(self):

        # Rich text + external links
        self.credit_lbl.setTextFormat(Qt.TextFormat.RichText)
        self.credit_lbl.setOpenExternalLinks(True)
        self.credit_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.credit_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Content (no inline style!)
        self.credit_lbl.setText("Powered by <a href='https://open-meteo.com/'>Open-Meteo</a>")

        # Only non-color styling here so we don't override palette
        self.credit_lbl.setStyleSheet("font-size: 11px; margin-top: 4px; background: transparent;")

        self.credit_lbl.update()
        self.refresh_footer()

    def apply_theme_to_tabs(self):
        t = self.app_ref.theme
        tab_bg = t.value("tab_bg", "rgba(255,255,255,10)")
        tab_sel_bg = t.value("tab_bg_selected", "rgba(255,255,255,18)")
        tab_color = t.value("tab_text", "#E6E8EE")
        tab_border = t.value("tab_border", "rgba(255,255,255,25)")
        qss = f"""
            QTabWidget::pane{{border:0;}}
            QTabBar::tab{{
                background:{tab_bg};
                color:{tab_color};
                border:1px solid {tab_border};
                border-bottom:0;
                border-radius:10px;
                padding:6px 16px;
                margin-right:2px;
            }}
            QTabBar::tab:selected{{
                background:{tab_sel_bg};
            }}
        """
        self.tabs.setStyleSheet(qss)

    def handle_window_drag(self, event):
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            handle = self.windowHandle()
            if handle and handle.startSystemMove():
                return True
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            return True
        if event.type() == QEvent.Type.MouseMove and self._drag_offset is not None:
            if event.buttons() & Qt.MouseButton.LeftButton:
                self.move(event.globalPosition().toPoint() - self._drag_offset)
                return True
        if event.type() == QEvent.Type.MouseButtonRelease and self._drag_offset is not None:
            self._drag_offset = None
            self.save_window_geometry()
            return True
        return False

    def closeEvent(self, event):
        # Alt+F4 closes the panel, while Quit remains in the tray menu.
        event.ignore()
        self.save_window_geometry()
        self.hide()

    def eventFilter(self, obj, event):
        if self.handle_window_drag(event):
            return True
        # Drag filters also watch labels and cards. Only tab containers need
        # a background gradient; painting it on each label creates dark bands.
        is_container = any(obj is data["container"] for data in self.city_tabs.values())
        if event.type() == QEvent.Type.Paint and is_container:
            p = QPainter(obj)
            g = QLinearGradient(0, 0, 0, obj.height())
            c0, c1 = self.app_ref.theme.value("background_gradient", ["#12141A", "#1A2036"])
            g.setColorAt(0, self.app_ref.theme.parse_color(c0))
            g.setColorAt(1, self.app_ref.theme.parse_color(c1))
            p.fillRect(obj.rect(), g)
            p.end()
            return False
        return super().eventFilter(obj, event)

    def retheme(self):
        self.apply_theme_to_tabs()
        self.apply_theme_to_credit()
        for data in self.city_tabs.values():
            card: GlassCard = data.get("card")
            if card:
                card.apply_theme_to_card()
                card.update()
                card.repaint()
        # Rebuild rich text using the new accent colors as well as label styles.
        for city, data in list(self.city_tabs.items()):
            if "info" in data:
                self.update_city_tab(city, data["info"])
        self.update()
        self.repaint()

    def paintEvent(self, e):
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, self.height())
        col0, col1 = self.app_ref.theme.value("background_gradient", ["#12141A", "#1A2036"])
        g.setColorAt(0, self.app_ref.theme.parse_color(col0))
        g.setColorAt(1, self.app_ref.theme.parse_color(col1))
        p.fillRect(self.rect(), g)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.repaint()
        self.refresh_footer()
        for data in self.city_tabs.values():
            card = data.get("card")
            if card:
                card.repaint()

    # ---------- Window Save/Restore ----------
    def save_window_geometry(self):
        pos, size = self.pos(), self.size()
        self.app_ref.config["window_pos"] = [pos.x(), pos.y()]
        self.app_ref.config["window_size"] = [size.width(), size.height()]
        self.app_ref.save_config()

    def get_tab_city_order(self) -> list[str]:
        ordered = []
        for i in range(self.tabs.count()):
            label = self.tabs.tabText(i)
            if label == "+":
                continue
            for city, data in self.city_tabs.items():
                if data.get("container") == self.tabs.widget(i):
                    ordered.append(city)
                    break
        return ordered

    # ---------- Tabs ----------
    def add_city_tab(self, city):
        if city in self.city_tabs:
            return
        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        container.setStyleSheet("background: transparent;")
        container.installEventFilter(self)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 8, 0, 8)
        lay.setSpacing(0)
        switches = QHBoxLayout()
        switches.setSpacing(0)
        current_button = QPushButton("Current")
        forecast_button = QPushButton("Forecast")
        for button in (current_button, forecast_button):
            button.setCheckable(True)
            button.setFixedHeight(26)
            button.setMinimumWidth(88)
            button.setStyleSheet("QPushButton { padding:2px 12px; } QPushButton:checked { border-width:2px; font-weight:bold; }")
            switches.addWidget(button)
        switches.addStretch()
        lay.addLayout(switches)
        card = GlassCard(self.app_ref)
        current_button.clicked.connect(lambda: self.select_forecast(False))
        forecast_button.clicked.connect(lambda: self.select_forecast(True))
        for child in [card, *card.findChildren(QWidget)]:
            if not isinstance(child, (QToolButton, QPushButton)):
                child.installEventFilter(self)
        lay.addWidget(card)
        lay.addSpacing(2)
        idx = self.tabs.count() - 1 if self.has_fake_tab() else self.tabs.count()
        location = getattr(self.app_ref, "locations", {}).get(city)
        label = location.get("name", city) if location else city.split(",")[0]
        with QSignalBlocker(self.tabs):
            self.tabs.insertTab(idx, container, label)
            self.tabs.setCurrentIndex(idx)
        card.city_lbl.setText(label)
        card.forecast_panel.set_weather({"city": label, "location": location or {}})
        close_btn = QToolButton()
        close_btn.setText("x")
        close_btn.setToolTip("Close tab")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedSize(24, 20)
        close_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                font-size: 10pt;
                font-weight: bold;
                margin-right: 4px;
                margin-top: -5px;
            }
            QToolButton:hover {
                background: rgba(255,255,255,25);
                border-radius: 11px;
            }
        """)
        close_btn.clicked.connect(lambda _, w=container: self.remove_tab_by_widget(w))
        self.tabs.tabBar().setTabButton(idx, QTabBar.ButtonPosition.RightSide, close_btn)
        self.city_tabs[city] = {"card": card, "container": container, "city": city, "state": "empty",
                                "current_button": current_button, "forecast_button": forecast_button}

        self.apply_forecast_selection()

    def apply_forecast_selection(self):
        enabled = bool(self.app_ref.config.get("forecast_mode", False))
        for data in self.city_tabs.values():
            data["current_button"].setChecked(not enabled)
            data["forecast_button"].setChecked(enabled)
            data["card"].set_forecast_mode(enabled)

    def select_forecast(self, enabled):
        self.app_ref.config["forecast_mode"] = bool(enabled)
        self.apply_forecast_selection()
        self.app_ref.save_config()
        self.settle_view_size()

    def tabs_reordered(self, *_):
        placeholder = next((i for i in range(self.tabs.count()) if self.tabs.tabText(i) == "+"), -1)
        if placeholder >= 0 and placeholder != self.tabs.count() - 1:
            with QSignalBlocker(self.tabs), QSignalBlocker(self.tabs.tabBar()):
                self.tabs.tabBar().moveTab(placeholder, self.tabs.count() - 1)
        self.app_ref.cities = self.get_tab_city_order()
        self.app_ref.save_config()
        self.update_tray_temperature()

    def update_tray_temperature(self):
        tray = getattr(self.app_ref, "tray", None)
        if not tray:
            return
        cities = self.app_ref.cities
        if not cities:
            tray.setIcon(create_temperature_icon(None) if self.app_ref.config.get("tray_display") == "temperature" else create_tray_icon("🌍"))
            tray.setToolTip("TrayWeatherApp · No cities configured")
            return
        city = cities[0]
        data = self.city_tabs.get(city, {})
        info = data.get("info", {})
        if self.app_ref.config.get("tray_display") == "temperature":
            tray.setIcon(create_temperature_icon(info.get("temp")))
        else:
            tray.setIcon(create_tray_icon(info.get("icon") or "🌍"))
        name = info.get("city") or getattr(self.app_ref, "locations", {}).get(city, {}).get("name", city)
        card = data.get("card")
        temperature = card.temp_lbl.text() if card else "—"
        state = card.status_lbl.text() if card else "Waiting for weather"
        location = info.get("location") or getattr(self.app_ref, "locations", {}).get(city, {})
        city_name = location.get("name") or name.split(",")[0]
        conditions = info.get("desc", "-").capitalize()
        # Native tray tooltips differ across desktops; plain text with explicit
        # lines stays readable without relying on unsupported HTML styling.
        status, separator, updated = state.partition(" · Updated ")
        freshness = f"{status}\nUpdated {updated}" if separator else status
        tray.setToolTip(f"{city_name}\n{temperature} · {conditions}\n\n{freshness}")

    def remove_tab_by_widget(self, widget):
        idx = self.tabs.indexOf(widget)
        if idx != -1:
            self.remove_tab(idx)

    def remove_tab(self, index):
        widget = self.tabs.widget(index)
        # Weather responses can change the visible label. The container remains
        # the stable link to the original city key used by jobs and settings.
        city = next((key for key, data in self.city_tabs.items()
                     if data["container"] is widget), None)
        if city is None:
            return  # Invalid index or the "+" placeholder.
        if city in self.app_ref.jobs:
            self.app_ref.cleanup_job(city)
        del self.city_tabs[city]
        # Selecting "+" as a side effect of removal must not open Add City.
        with QSignalBlocker(self.tabs):
            self.tabs.removeTab(index)
        widget.deleteLater()
        if city in self.app_ref.cities:
            self.app_ref.cities.remove(city)
            getattr(self.app_ref, "locations", {}).pop(city, None)
            self.app_ref.save_config()
        self.update_tray_temperature()
        self.refresh_footer()

    def add_fake_tab(self):
        fake = QWidget()
        with QSignalBlocker(self.tabs):
            self.tabs.addTab(fake, "+")
        self.tabs.tabBar().setTabButton(self.tabs.indexOf(fake), QTabBar.ButtonPosition.RightSide, None)

    def has_fake_tab(self):
        return self.tabs.count() > 0 and self.tabs.tabText(self.tabs.count() - 1) == "+"

    def click_tab(self, index):
        # When no cities remain, "+" is already selected and currentChanged
        # cannot fire. Avoid a second dialog when selection already handled it.
        if self.tabs.count() == 1:
            self.check_fake_tab(index)

    def check_fake_tab(self, index):
        if self.has_fake_tab() and index == self.tabs.count() - 1:
            # Move off the placeholder before entering the modal dialog.
            if self.tabs.count() > 1:
                with QSignalBlocker(self.tabs):
                    self.tabs.setCurrentIndex(0)
            dialog = CitySearchDialog(self)
            if dialog.exec() and dialog.selected_location:
                self.app_ref.add_location(dialog.selected_location)
            dialog.deleteLater()

    # ---------- Update Cards ----------
    def update_city_tab(self, city, info):
        if city not in self.city_tabs:
            return
        data = self.city_tabs[city]
        card = data.get("card")
        if not card or not hasattr(card, "city_lbl"):
            return

        self.city_tabs[city]["info"] = info
        card.forecast_panel.set_weather(info)
        temp_label, wind_label = ("C", "km/h") if self.app_ref.units == "metric" else ("F", "mph")
        tab_idx = self.tabs.indexOf(data["container"])
        full_name = info.get("city", city)
        location = info.get("location") or getattr(self.app_ref, "locations", {}).get(city, {})
        city_name = location.get("name") or full_name.split(",")[0]
        if tab_idx != -1:
            self.tabs.setTabText(tab_idx, city_name)
            self.tabs.setTabToolTip(tab_idx, full_name)

        card.city_lbl.setText(city_name)
        card.city_lbl.setToolTip(full_name)
        t = info.get("temp")
        card.temp_lbl.setText(f"{t:.1f}°{temp_label}" if isinstance(t, (int, float)) else "-°")
        card.desc_lbl.setText(info.get("desc", "-").capitalize())
        f = info.get("feels_like", "-")
        h = info.get("humidity", "-")
        w = info.get("wind_speed", "-")
        H = info.get("high", "-")
        L = info.get("low", "-")
        card.more_lbl.setText(card.themed_detail_html(f, H, L, h, w, temp_label, wind_label))
        card.tz_offset = info.get("timezone", 0)
        self.update_card_time(card)
        if not hasattr(card, "time_timer"):
            card.time_timer = QTimer(card)
            card.time_timer.timeout.connect(lambda c=card: self.update_card_time(c))
            card.time_timer.start(60000)
        emoji = info.get("icon", "🌍")
        s = max(120, min(220, int(self.height() * 0.4)))
        card.icon_lbl.setPixmap(QPixmap())
        card.icon_lbl.setText(emoji)
        card.icon_lbl.setFont(QFont("Segoe UI Emoji", int(s * 0.8)))
        card.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_card_scaling()
        self.update_freshness(city)

    def update_card_time(self, card):
        fmt_24h = self.app_ref.config.get("time_format_24h", True)
        now_utc = datetime.now(timezone.utc)
        dt = now_utc + timedelta(seconds=getattr(card, "tz_offset", 0))
        timestr = dt.strftime("%H:%M") if fmt_24h else dt.strftime("%I:%M %p")
        card.time_lbl.setText(f"🕒 {timestr}")
        for city, data in self.city_tabs.items():
            if data["card"] is card:
                self.update_freshness(city)
                break

    def clear_weather(self, city):
        data = self.city_tabs.get(city)
        if not data:
            return
        data.pop("info", None)
        data["card"].forecast_panel.set_weather({"city": data["card"].city_lbl.text()})
        card = data["card"]
        card.temp_lbl.setText("-°")
        card.desc_lbl.setText("-")
        card.more_lbl.setText("-")
        card._compact_summary = "Feels —  ·  High — / Low —"
        card.compact_summary.setToolTip("")
        data["state"] = "empty"
        self.update_freshness(city)

    def set_weather_state(self, city, state, error=""):
        data = self.city_tabs.get(city)
        if data:
            data["state"], data["error"] = state, error
            self.update_freshness(city)

    def update_freshness(self, city):
        data = self.city_tabs.get(city)
        if not data:
            return
        timestamp = parse_timestamp(data.get("info", {}).get("updated_at"))
        state = data.get("state", "empty")
        if timestamp:
            minutes = max(0, int((datetime.now(timezone.utc) - timestamp).total_seconds() / 60))
            last = timestamp.astimezone().strftime(
                "%H:%M" if self.app_ref.config.get("time_format_24h") else "%I:%M %p")
            old = minutes >= 30
            status = ("Refreshing…" if state == "refreshing" else
                      "Unable to refresh · saved weather" if state == "error" else
                      "Cached weather" if state == "cached" else
                      "Stale weather" if old else "Up to date")
            text = f"{status} · Updated {last} ({minutes} min ago)"
            if old and state != "live":
                text += " · stale"
        else:
            text = ("Refreshing…" if state == "refreshing" else
                    "Unable to refresh · no saved weather" if state == "error" else
                    "Waiting for weather")
        card = data["card"]
        card.status_lbl.setText(text)
        card.sync_compact()
        compact_text = (f"● Updated {last}" if timestamp and state == "live" and not old else
                        "● Refreshing…" if state == "refreshing" else
                        f"● Cached · {last}" if timestamp and state == "cached" else
                        f"● Stale · {last}" if timestamp and old and state != "error" else
                        "● Unable to refresh" if state == "error" else
                        "Waiting for weather")
        card.compact_status.setText(compact_text)
        card.compact_status.setToolTip(text + (" · " + data.get("error", "") if data.get("error") else ""))
        card.compact_status.setStyleSheet(
            f"color:{'#75C991' if timestamp and state == 'live' and not old else '#E7B76B'}; background:transparent;")
        self.refresh_footer()
        card.status_lbl.setToolTip(data.get("error", "") or
                                  "Time of the last successful download, shown in your computer's local time.")
        self.update_tray_temperature()

    def update_card_scaling(self):
        for data in self.city_tabs.values():
            data["card"].apply_responsive_layout()
