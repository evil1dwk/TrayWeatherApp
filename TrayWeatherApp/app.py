# TrayWeatherApp module: app.py

from datetime import datetime, timezone, timedelta
from PyQt6.QtCore import Qt, QTimer, QThread
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from TrayWeatherApp.config_utils import log, CONFIG_PATH, DEFAULT_CONFIG, create_tray_icon
from TrayWeatherApp.settings import SettingsDialog
from TrayWeatherApp.theme import ThemeManager
from TrayWeatherApp.weather import WeatherWindow
from TrayWeatherApp.workers import WeatherWorker
import sys, json

# ---------- Main App ----------
class TrayWeatherApp:
    REFRESH_INTERVAL_MS = 15 * 60 * 1000

    def __init__(self):
        self.app = QApplication(sys.argv)
        from ._version import __version__
        self.app.setApplicationVersion(__version__)
        self.app.setQuitOnLastWindowClosed(False)
        self.theme = ThemeManager()
        self.load_config()

        self.theme.select_theme(self.config.get("theme", "System"))
        self.theme.apply_to_app(self.app)

        self.window = WeatherWindow(self)
        self.theme.changed.connect(self.window.retheme)
        self.tray = QSystemTrayIcon(create_tray_icon("☀️"))
        self.tray.setToolTip("TrayWeatherApp")
        self.tray.activated.connect(self.on_tray_activated)
        menu = QMenu()
        menu.addAction("Show/Hide Window", self.toggle_window)
        menu.addAction("Refresh", self.fetch_weather_now)
        menu.addAction("Settings", self.open_settings)
        menu.addAction("About TrayWeatherApp", self.show_about)
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

    def load_config(self):
        from copy import deepcopy
        self.config = deepcopy(DEFAULT_CONFIG)
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
            "theme": self.config.get("theme", "System"),
        })
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(json.dumps(self.config, indent=2), encoding="utf-8")
        except Exception as e:
            log(f"Config save error: {e}", "ERROR")

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
                self.theme.select_theme(vals["theme"])
                self.config["theme"] = self.theme.current_name
                if self.theme.last_error:
                    QMessageBox.warning(None, "Theme unavailable", self.theme.last_error)
            self.config["debug"] = vals["debug"]
            self.config["time_format_24h"] = vals["time_format_24h"]
            self.time_format_24h = vals["time_format_24h"]
            self.save_config()
            for data in self.window.city_tabs.values():
                self.window.update_card_time(data["card"])
            self.fetch_weather_now()

    def show_about(self):
        from ._version import __version__
        QMessageBox.about(
            self.window, "About TrayWeatherApp",
            f"<h3>TrayWeatherApp {__version__}</h3>"
            "<p>Created by evil1dwk</p><p>Weather data from Open-Meteo.</p>"
            "<p><a href='https://github.com/evil1dwk/TrayWeatherApp'>Project</a>"
            " · <a href='https://github.com/evil1dwk/TrayWeatherApp/issues'>Report an issue</a></p>")

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
    app.run()
