# TrayWeatherApp module: weather.py

from PyQt6.QtCore import Qt
from datetime import datetime, timezone, timedelta
from PyQt6.QtCore import Qt, QTimer, QSignalBlocker
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
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        self.move(*app_ref.config.get("window_pos", [100, 100]))
        enable_windows_acrylic(self)

        self.tabs = QTabWidget()
        self.tabs.setMovable(True)
        self.tabs.setTabsClosable(True)
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
        available = max(0, self.width() - 36 - self.credit_lbl.sizeHint().width() - 12)
        self.footer_status.setText(self.footer_status.fontMetrics().elidedText(
            text, Qt.TextElideMode.ElideRight, available))
        self.footer_status.setToolTip(tooltip)
        color = self.app_ref.theme.value("text_muted", "#9EA3B8")
        self.footer_status.setStyleSheet(f"color:{color}; font-size:11px; margin-top:4px; background:transparent;")

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

    def eventFilter(self, obj, event):
        if event.type() == event.Type.Paint and isinstance(obj, QWidget):
            p = QPainter(obj)
            g = QLinearGradient(0, 0, 0, obj.height())
            c0, c1 = self.app_ref.theme.value("background_gradient", ["#12141A", "#1A2036"])
            g.setColorAt(0, self.app_ref.theme.parse_color(c0))
            g.setColorAt(1, self.app_ref.theme.parse_color(c1))
            p.fillRect(obj.rect(), g)
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
        card = GlassCard(self.app_ref)
        lay.addWidget(card)
        lay.addSpacing(8)  # fixed spacing (no dark band)
        idx = self.tabs.count() - 1 if self.has_fake_tab() else self.tabs.count()
        location = getattr(self.app_ref, "locations", {}).get(city)
        label = location.get("name", city) if location else city.split(",")[0]
        with QSignalBlocker(self.tabs):
            self.tabs.insertTab(idx, container, label)
            self.tabs.setCurrentIndex(idx)
        card.city_lbl.setText(label)
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
        self.city_tabs[city] = {"card": card, "container": container, "city": city, "state": "empty"}

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
        if getattr(self.app_ref, "tray", None) and self.app_ref.cities:
            first_city = self.app_ref.cities[0]
            if city == first_city:
                emoji_tray = info.get("icon") or "🌍"
                t = info.get("temp")
                tt_temp = f"{t:.1f}°" if isinstance(t, (int, float)) else "-°"
                self.app_ref.tray.setIcon(QIcon())
                self.app_ref.tray.setIcon(create_tray_icon(emoji_tray))
                self.app_ref.tray.setToolTip(
                    f"{info.get('city', first_city)} • {info.get('desc', '-').capitalize()} • {tt_temp}"
                )
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
        if getattr(self.app_ref, "tray", None) and self.app_ref.cities and city == self.app_ref.cities[0]:
            info = data.get("info", {})
            self.app_ref.tray.setToolTip(f"{info.get('city', city)} · {card.temp_lbl.text()} · {text}")

    def update_card_scaling(self):
        for data in self.city_tabs.values():
            data["card"].apply_responsive_layout()
