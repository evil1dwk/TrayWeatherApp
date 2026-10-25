# TrayWeatherApp module: app.py

from datetime import datetime, timezone, timedelta
from PyQt6.QtCore import Qt, QTimer, QThread, QObject, pyqtSlot
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from TrayWeatherApp.config_utils import log, CONFIG_PATH, DEFAULT_CONFIG, create_tray_icon
from TrayWeatherApp.settings import SettingsDialog
from TrayWeatherApp.theme import ThemeManager
from TrayWeatherApp.weather import WeatherWindow
from TrayWeatherApp.workers import WeatherWorker, location_label
from TrayWeatherApp.weather_cache import WeatherCache
from uuid import uuid4
import sys, json

# ---------- Main App ----------
class TrayWeatherApp(QObject):
    REFRESH_INTERVAL_MS = 15 * 60 * 1000

    def __init__(self):
        super().__init__()
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
        menu.addAction("Quit", self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.show()
        self.jobs = {}
        self._threads = set()
        self._quitting = False
        self.cache = WeatherCache()
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
        self.locations = self.config.get("locations", {})
        self.units   = self.config.get("units", "imperial")
        self.time_format_24h = self.config.get("time_format_24h", False)

    def save_config(self):
        self.config.update({
            "cities": self.cities,
            "locations": self.locations,
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
        if city in self.jobs and self.jobs[city]["units"] == self.units:
            return
        if city in self.jobs:
            self.cleanup_job(city)
        location = self.locations.get(city)
        cached = self.cache.get(city, self.units, location)
        current = self.window.city_tabs.get(city, {}).get("info")
        if cached and (not current or current.get("units") != self.units):
            self.window.update_city_tab(city, cached)
            self.window.set_weather_state(city, "cached")
        elif current and current.get("units") != self.units:
            self.window.clear_weather(city)
        self.window.set_weather_state(city, "refreshing")
        token = uuid4().hex
        worker = WeatherWorker(city, self.units, location, token)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.worker = worker  # Keep the worker alive even after a tab cancels its job.
        self.jobs[city] = {"thread": thread, "worker": worker, "units": self.units, "token": token}
        self._threads.add(thread)
        thread.started.connect(worker.run)
        worker.result.connect(self.weather_result)
        worker.done.connect(thread.quit)
        worker.done.connect(worker.deleteLater)
        thread.finished.connect(self.thread_finished)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    @pyqtSlot(str, object)
    def weather_result(self, city, info):
        # A city may have been closed/re-added, or units changed during the request.
        job = self.jobs.get(city)
        if (not job or info.get("request_id") != job["token"]
                or info.get("units") != self.units or city not in self.window.city_tabs):
            return
        self.jobs.pop(city, None)
        if "error" in info:
            self.window.set_weather_state(city, "error", info["error"])
            return
        location = info.get("location")
        if location and city not in self.locations:
            self.locations[city] = location
            self.save_config()
        try:
            self.cache.put(city, self.units, info, self.locations.get(city))
        except (OSError, ValueError) as exc:
            log(f"Weather cache save failed: {exc}", "ERROR")
        self.window.update_city_tab(city, info)
        self.window.set_weather_state(city, "live")

    @pyqtSlot()
    def thread_finished(self):
        thread = self.sender()
        self._threads.discard(thread)
        thread.worker = None
        for city, job in list(self.jobs.items()):
            if job["thread"] is thread:
                self.jobs.pop(city)
        if self._quitting and not self._threads:
            self.app.quit()

    def cleanup_job(self, city: str):
        job = self.jobs.pop(city, None)
        if job:
            # requests has a timeout; keep the QThread alive until it finishes.
            job["thread"].requestInterruption()

    def add_location(self, location):
        key = (f"geo:{location['id']}" if location.get("id") is not None
               else f"geo:{location['latitude']}:{location['longitude']}")
        for existing in self.cities:
            saved = self.locations.get(existing, {})
            if (saved.get("latitude"), saved.get("longitude")) == (location["latitude"], location["longitude"]):
                key = existing
                break
        if key not in self.cities:
            self.cities.append(key)
            self.locations[key] = dict(location)
            self.save_config()
            self.window.add_city_tab(key)
            self.fetch_weather_city(key)
        data = self.window.city_tabs[key]
        self.window.tabs.setCurrentWidget(data["container"])

    def toggle_window(self):
        if self.window.isVisible():
            self.window.save_window_geometry()
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
            old_units = self.units
            self.units = vals["units"]
            self.config["view_mode"] = vals.get("view_mode", "normal")
            self.config["tray_display"] = vals.get("tray_display", "icon")
            self.window.apply_view_mode()
            if old_units != self.units:
                for city in list(self.cities):
                    cached = self.cache.get(city, self.units, self.locations.get(city))
                    self.window.clear_weather(city)
                    if cached:
                        self.window.update_city_tab(city, cached)
                        self.window.set_weather_state(city, "cached")
            if vals["theme"]:
                self.theme.select_theme(vals["theme"])
                self.config["theme"] = self.theme.current_name
                if self.theme.last_error:
                    QMessageBox.warning(None, "Theme unavailable", self.theme.last_error)
            self.config["debug"] = vals["debug"]
            self.config["time_format_24h"] = vals["time_format_24h"]
            self.time_format_24h = vals["time_format_24h"]
            self.save_config()
            self.window.update_tray_temperature()
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
        self._quitting = True
        self.timer.stop()
        self.window.hide()
        self.tray.hide()
        if not self._threads:
            self.app.quit()

    def run(self):
        sys.exit(self.app.exec())

# ---------- Run ----------
if __name__ == "__main__":
    log("=== Weather Tray App Started ===")
    app = TrayWeatherApp()
    app.run()
