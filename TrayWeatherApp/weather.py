# TrayWeatherApp module: weather.py

from PyQt6.QtCore import Qt
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
from TrayWeatherApp.ui_components import GlassCard

# ---------- Weather Window ----------
class WeatherWindow(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref
        self.city_tabs = {}
        self.setWindowTitle("TrayWeatherApp")
        set_sun_icon(self)
        self.resize(*app_ref.config.get("window_size", [760, 440]))
        self.move(*app_ref.config.get("window_pos", [100, 100]))
        enable_windows_acrylic(self)

        self.tabs = QTabWidget()
        self.tabs.setMovable(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.remove_tab)
        self.tabs.currentChanged.connect(self.check_fake_tab)
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
        lay.addWidget(self.credit_lbl, alignment=Qt.AlignmentFlag.AlignRight)

        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(False)

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
            g.setColorAt(0, QColor(c0))
            g.setColorAt(1, QColor(c1))
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
        self.update()
        self.repaint()

    def paintEvent(self, e):
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, self.height())
        col0, col1 = self.app_ref.theme.value("background_gradient", ["#12141A", "#1A2036"])
        g.setColorAt(0, QColor(col0))
        g.setColorAt(1, QColor(col1))
        p.fillRect(self.rect(), g)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.repaint()
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
        self.tabs.insertTab(idx, container, city)
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
        self.city_tabs[city] = {"card": card, "container": container, "city": city}

    def remove_tab_by_widget(self, widget):
        idx = self.tabs.indexOf(widget)
        if idx != -1:
            self.remove_tab(idx)

    def remove_tab(self, index):
        city = self.tabs.tabText(index)
        widget = self.tabs.widget(index)
        if city in self.app_ref.jobs:
            self.app_ref.cleanup_job(city)
        if city in self.city_tabs:
            del self.city_tabs[city]
        self.tabs.removeTab(index)
        if widget:
            widget.deleteLater()
        if city in self.app_ref.cities:
            self.app_ref.cities.remove(city)
            self.app_ref.save_config()

    def add_fake_tab(self):
        fake = QWidget()
        self.tabs.addTab(fake, "+")
        self.tabs.tabBar().setTabButton(self.tabs.indexOf(fake), QTabBar.ButtonPosition.RightSide, None)

    def has_fake_tab(self):
        return self.tabs.count() > 0 and self.tabs.tabText(self.tabs.count() - 1) == "+"

    def check_fake_tab(self, index):
        if self.has_fake_tab() and index == self.tabs.count() - 1:
            city, ok = QInputDialog.getText(self, "Add City", "Enter city (e.g., New York):")
            if ok and city:
                city = city.strip()
                if city and city not in self.app_ref.cities:
                    self.app_ref.cities.append(city)
                    self.app_ref.save_config()
                    self.add_city_tab(city)
                    self.app_ref.fetch_weather_city(city)
            if self.tabs.count() > 1:
                self.tabs.setCurrentIndex(0)

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
        if tab_idx != -1:
            self.tabs.setTabText(tab_idx, info.get("city", city))

        card.city_lbl.setText(info.get("city", city))
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

    def update_card_time(self, card):
        fmt_24h = self.app_ref.config.get("time_format_24h", True)
        now_utc = datetime.now(timezone.utc)
        dt = now_utc + timedelta(seconds=getattr(card, "tz_offset", 0))
        timestr = dt.strftime("%H:%M") if fmt_24h else dt.strftime("%I:%M %p")
        card.time_lbl.setText(f"🕒 {timestr}")

    def update_card_scaling(self):
        if not hasattr(self, "city_tabs"):
            return
        base = max(10, self.height() // 30)
        for city, data in list(self.city_tabs.items()):
            try:
                card: GlassCard = data.get("card")
                if not card or not hasattr(card, "city_lbl"):
                    continue
                card.city_lbl.setFont(QFont("Segoe UI", base + 10, QFont.Weight.Bold))
                card.temp_lbl.setFont(QFont("Segoe UI", base + 26, QFont.Weight.DemiBold))
                card.desc_lbl.setFont(QFont("Segoe UI", base + 4))
                card.more_lbl.setFont(QFont("Segoe UI", base + 2))
                card.time_lbl.setFont(QFont("Segoe UI", max(12, base + 2)))
                iw = max(160, min(260, int(self.width() * 0.22)))
                card.icon_lbl.setMinimumWidth(iw)
            except RuntimeError as e:
                log(f"Ignored scaling for deleted card {city}: {e}", "DEBUG")
                continue
