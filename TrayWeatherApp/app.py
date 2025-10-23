import sys, io, json
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore import QTimer, QThread
from .config_utils import log, load_config, save_config, CONFIG_PATH, THEMES_DIR, DEFAULT_CONFIG, zipfile, create_tray_icon
from datetime import datetime, timezone, timedelta

from .theme import ThemeManager
from .config_utils import log, load_config, save_config
from .weather import WeatherWindow
from .settings import SettingsDialog
from .workers import WeatherWorker

# ---------- Main App ----------
class TrayWeatherApp:
    REFRESH_INTERVAL_MS = 15 * 60 * 1000

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.theme = ThemeManager()
        self.load_config()

        self.ensure_example_themes()

        try:
            self.theme.load_theme(self.config.get("theme", "dark"))
        except Exception as e:
            log(f"Theme load failed: {e}", "ERROR")
        self.theme.apply_to_app(self.app)

        self.window = WeatherWindow(self)
        self.tray = QSystemTrayIcon(create_tray_icon("☀️"))
        self.tray.setToolTip("TrayWeatherApp")
        self.tray.activated.connect(self.on_tray_activated)
        menu = QMenu()
        menu.addAction("Show/Hide Window", self.toggle_window)
        menu.addAction("Refresh", self.fetch_weather_now)
        menu.addAction("Settings", self.open_settings)
        menu.addAction("Quit", self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.show()
        self.jobs = {}
        for city in self.cities:
            self.window.add_city_tab(city)
            self.fetch_weather_city(city)
        self.window.add_fake_tab()
        self.timer = QTimer()
        self.timer.setInterval(self.REFRESH_INTERVAL_MS)
        self.timer.timeout.connect(self.fetch_weather_now)
        self.timer.start()

    def ensure_example_themes(self):
        if list(THEMES_DIR.glob("*.zip")):
            return
        log("No themes found; generating example themes (dark, light, solarized)")
        def make_theme_zip(name, css_text, json_dict):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr(f"{name}.css", css_text)
                z.writestr(f"{name}.json", json.dumps(json_dict, indent=2))
            (THEMES_DIR / f"{name}.zip").write_bytes(buf.getvalue())

        base_qss = """
QWidget { font-family: "Segoe UI", "Helvetica Neue", Arial; }
QMenu {
  background-color: rgba(30,32,40,230);
  border: 1px solid rgba(255,255,255,25);
}
QMenu::item { padding: 8px 16px; }
QMenu::item:selected { background: rgba(255,255,255,0.1); }
QDialog { background-color: #1E2028; }
QLineEdit, QComboBox {
  background: rgba(255,255,255,10);
  border: 1px solid rgba(255,255,255,30);
  border-radius: 8px;
  padding: 6px 8px;
  color: #E6E8EE;
}
QPushButton {
  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
    stop:0 rgba(255,255,255,22), stop:1 rgba(255,255,255,12));
  border: 1px solid rgba(255,255,255,35);
  color: #E6E8EE;
  border-radius: 10px;
  padding: 8px 14px;
}
QPushButton:hover { background: rgba(255,255,255,22); }
QPushButton:pressed { background: rgba(255,255,255,14); }
QCheckBox { spacing: 8px; }
"""
        dark_json = {
          "name": "Dark",
          "background_gradient": ["#12141A", "#1A2036"],
          "glass_card_color": "rgba(20,22,30,150)",
          "card_border_color": "rgba(255,255,255,25)",
          "text_primary": "#E6E8EE",
          "text_muted": "#9EA3B8",
          "text_desc": "#C5C9D3",
          "text_more": "#A8AFC2",
          "temp_color": "#FFD18A",
          "high_color": "#FFB347",
          "low_color": "#7DD3FC",
          "humid_color": "#7DD3FC",
          "wind_color": "#C4B5FD",
          "accent_glow": "#FFC878",
          "link_color": "#7DD3FC",
          "tab_bg": "rgba(255,255,255,0.10)",
          "tab_bg_selected": "rgba(255,255,255,0.18)",
          "tab_text": "#E6E8EE",
          "tab_border": "rgba(255,255,255,0.25)"
        }
        light_qss = """
QWidget { color: #212121; font-family: "Segoe UI", "Helvetica Neue", Arial; }
QMenu {
  background-color: rgba(255,255,255,0.98);
  border: 1px solid rgba(0,0,0,40);
}
QMenu::item { padding: 8px 16px; }
QMenu::item:selected { background: rgba(0,0,0,0.08); }
QDialog { background-color: #F7F9FB; }
QLineEdit, QComboBox {
  background: rgba(0,0,0,0.05);
  border: 1px solid rgba(0,0,0,0.12);
  border-radius: 8px;
  padding: 6px 8px;
  color: #212121;
}
QPushButton {
  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
    stop:0 rgba(0,0,0,0.05), stop:1 rgba(0,0,0,0.03));
  border: 1px solid rgba(0,0,0,0.15);
  color: #212121;
  border-radius: 10px;
  padding: 8px 14px;
}
QPushButton:hover { background: rgba(0,0,0,0.08); }
QPushButton:pressed { background: rgba(0,0,0,0.05); }
QCheckBox { spacing: 8px; }
"""
        light_json = {
          "name": "Light",
          "background_gradient": ["#F2F4F8", "#DDE3EE"],
          "glass_card_color": "rgba(245,247,250,200)",
          "card_border_color": "rgba(0,0,0,60)",
          "text_primary": "#212121",
          "text_muted": "#4E5D6C",
          "text_desc": "#37474F",
          "text_more": "#546E7A",
          "temp_color": "#E65100",
          "high_color": "#E57373",
          "low_color": "#039BE5",
          "humid_color": "#039BE5",
          "wind_color": "#7E57C2",
          "accent_glow": "#FFC107",
          "link_color": "#1976D2",
          "tab_bg": "rgba(0,0,0,0.08)",
          "tab_bg_selected": "rgba(0,0,0,0.15)",
          "tab_text": "#212121",
          "tab_border": "rgba(0,0,0,0.20)"
        }
        sol_json = {
          "name": "Solarized",
          "background_gradient": ["#002b36", "#073642"],
          "glass_card_color": "rgba(7,54,66,170)",
          "card_border_color": "rgba(147,161,161,90)",
          "text_primary": "#EEE8D5",
          "text_muted": "#93A1A1",
          "text_desc": "#E0E5C1",
          "text_more": "#B3C2B2",
          "temp_color": "#B58900",
          "high_color": "#CB4B16",
          "low_color":  "#268BD2",
          "humid_color":"#268BD2",
          "wind_color": "#6C71C4",
          "accent_glow": "#FABD2F",
          "link_color": "#2AA198",
          "tab_bg": "rgba(238,232,213,0.08)",
          "tab_bg_selected": "rgba(238,232,213,0.16)",
          "tab_text": "#EEE8D5",
          "tab_border": "rgba(238,232,213,0.25)"
        }
        def pack(name, css, j):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr(f"{name}.css", css)
                z.writestr(f"{name}.json", json.dumps(j, indent=2))
            (THEMES_DIR / f"{name}.zip").write_bytes(buf.getvalue())
        pack("dark", base_qss, dark_json)
        pack("light", light_qss, light_json)
        pack("solarized", base_qss, sol_json)

    def load_config(self):
        self.config = DEFAULT_CONFIG.copy()
        if CONFIG_PATH.exists():
            try:
                self.config.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
            except Exception as e:
                log(f"Config load failed: {e}", "ERROR")
        self.cities  = self.config.get("cities", ["New York"])
        self.units   = self.config.get("units", "imperial")
        self.time_format_24h = self.config.get("time_format_24h", False)

    def save_config(self):
        self.config.update({
            "cities": self.cities,
            "units": self.units,
            "time_format_24h": self.time_format_24h,
            "theme": self.config.get("theme", "dark"),
        })
        try:
            CONFIG_PATH.write_text(json.dumps(self.config, indent=2), encoding="utf-8")
        except Exception as e:
            log(f"Config save error: {e}", "ERROR")

    def apply_theme_now(self):
        self.theme.apply_to_app(self.app)
        if hasattr(self, "window"):
            self.window.retheme()
            for data in self.window.city_tabs.values():
                self.window.update_card_time(data["card"])

    def on_tray_activated(self, reason):
        if reason not in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            return
        now = datetime.now().timestamp()
        if hasattr(self, "_last_tray_click") and now - self._last_tray_click < 0.25:
            return
        self._last_tray_click = now
        self.toggle_window()

    def fetch_weather_now(self):
        for city in list(self.cities):
            self.fetch_weather_city(city)

    def fetch_weather_city(self, city: str):
        if city in self.jobs:
            return
        worker = WeatherWorker(city, self.units)
        thread = QThread()
        worker.moveToThread(thread)
        self.jobs[city] = {"thread": thread, "worker": worker}
        thread.started.connect(worker.run)
        worker.finished.connect(lambda c, info: QTimer.singleShot(0, lambda: self.window.update_city_tab(c, info)))
        worker.error.connect(lambda c, msg: QTimer.singleShot(0, lambda: self.window.update_city_tab(c, {"desc": msg})))
        def _cleanup(): self.cleanup_job(city)
        worker.finished.connect(_cleanup); worker.error.connect(_cleanup)
        thread.start()

    def cleanup_job(self, city: str):
        obj = self.jobs.pop(city, None)
        if obj:
            worker, t = obj["worker"], obj["thread"]
            t.quit(); t.wait(150)
            try: worker.deleteLater()
            except Exception: pass
            try: t.deleteLater()
            except Exception: pass

    def toggle_window(self):
        if self.window.isVisible():
            self.window.hide()
        else:
            self.window.show()
            self.window.raise_()
            self.window.activateWindow()
            try:
                self.window.setWindowState(
                    self.window.windowState()
                    & ~Qt.WindowState.WindowMinimized
                    | Qt.WindowState.WindowActive
                )
            except Exception as e:
                log(f"Window state activation failed: {e}", "DEBUG")

    def open_settings(self):
        dlg = SettingsDialog(self.config, self.theme)
        if dlg.exec():
            vals = dlg.get_values()
            self.units   = vals["units"]
            if vals["theme"]:
                self.config["theme"] = vals["theme"]
                try:
                    self.theme.load_theme(vals["theme"])
                except Exception as e:
                    log(f"Theme reload failed: {e}", "ERROR")
                self.apply_theme_now()
            self.config["debug"] = vals["debug"]
            self.config["time_format_24h"] = vals["time_format_24h"]
            self.time_format_24h = vals["time_format_24h"]
            self.save_config()
            for data in self.window.city_tabs.values():
                self.window.update_card_time(data["card"])
            self.fetch_weather_now()

    def quit_app(self):
        log("Saving window geometry and city order before quitting")
        self.window.save_window_geometry()

        try:
            ordered = self.window.get_tab_city_order()
            self.cities = [c for c in ordered if c in self.cities]
            if ordered:
                self.config["cities"] = self.cities
                log(f"Saved tab order: {self.cities}")
            else:
                log("No city tabs found to save", "DEBUG")
        except Exception as e:
            log(f"Failed to save tab order: {e}", "ERROR")

        for city in list(self.jobs.keys()):
            self.cleanup_job(city)

        self.save_config()
        self.app.quit()

    def run(self):
        sys.exit(self.app.exec())

# ---------- Run ----------
if __name__ == "__main__":
    log("=== Weather Tray App Started ===")
    app = TrayWeatherApp()
    app.apply_theme_now()  # apply theme CSS at start
    app.run()
