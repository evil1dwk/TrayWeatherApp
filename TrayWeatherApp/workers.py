# TrayWeatherApp module: workers.py

from datetime import datetime, timezone, timedelta
from PyQt6.QtCore import QObject, pyqtSignal
from TrayWeatherApp.config_utils import log
import requests


# ---------- Weather Window ----------
class WeatherWorker(QObject):
    finished = pyqtSignal(str, object)
    error = pyqtSignal(str, str)

    def __init__(self, city: str, units: str):
        super().__init__()
        self.city = city
        self.units = units

    def run(self):
        try:
            geo_url = "https://geocoding-api.open-meteo.com/v1/search"
            rg = requests.get(geo_url, params={"name": self.city, "count": 1}, timeout=10)
            if rg.status_code != 200:
                self.error.emit(self.city, f"Geocode error {rg.status_code}")
                return
            geo = rg.json().get("results", [])
            if not geo:
                self.error.emit(self.city, f"City not found: {self.city}")
                return

            loc = geo[0]
            lat, lon = loc["latitude"], loc["longitude"]
            city_name = loc.get("name", self.city)
            country_code = loc.get("country_code") or loc.get("country", "")
            display_name = f"{city_name}, {country_code}".strip().strip(",")

            temp_unit = "celsius" if self.units == "metric" else "fahrenheit"
            wind_unit = "kmh" if self.units == "metric" else "mph"

            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": [
                    "temperature_2m", "apparent_temperature",
                    "relative_humidity_2m", "wind_speed_10m", "weather_code"
                ],
                "daily": ["temperature_2m_max", "temperature_2m_min", "weather_code"],
                "timezone": "auto",
                "temperature_unit": temp_unit,
                "wind_speed_unit": wind_unit,
            }

            r = requests.get(url, params=params, timeout=10)
            if r.status_code != 200:
                self.error.emit(self.city, f"Weather API error {r.status_code}")
                return
            d = r.json()
            cur, daily = d.get("current", {}), d.get("daily", {})

            tz_offset = d.get("utc_offset_seconds", 0)
            local_time = datetime.utcnow() + timedelta(seconds=tz_offset)
            hour = local_time.hour
            is_night = hour < 6 or hour >= 18  # 6 AM–6 PM heuristic

            desc, emoji = self.map_weather_code(cur.get("weather_code"), is_night=is_night)

            info = {
                "city": display_name,
                "temp": cur.get("temperature_2m"),
                "feels_like": cur.get("apparent_temperature"),
                "humidity": cur.get("relative_humidity_2m"),
                "wind_speed": cur.get("wind_speed_10m"),
                "desc": desc,
                "icon": emoji,
                "timezone": tz_offset,
                "high": (daily.get("temperature_2m_max") or [None])[0],
                "low": (daily.get("temperature_2m_min") or [None])[0],
            }
            self.finished.emit(self.city, info)

        except Exception as e:
            self.error.emit(self.city, str(e))

    def map_weather_code(self, code: int | None, is_night=False):
        if code is None:
            return ("Unknown", "🌍")

        mapping = {
            0: ("Clear sky", "🌙" if is_night else "☀️"),
            1: ("Mainly clear", "🌙" if is_night else "🌤️"),
            2: ("Partly cloudy", "☁️" if is_night else "⛅"),
            3: ("Overcast", "☁️"),
            45: ("Fog", "🌫️"),
            48: ("Rime fog", "🌫️"),
            51: ("Light drizzle", "🌦️"),
            53: ("Drizzle", "🌧️"),
            55: ("Heavy drizzle", "🌧️"),
            61: ("Light rain", "🌦️"),
            63: ("Rain", "🌧️"),
            65: ("Heavy rain", "🌧️"),
            71: ("Light snow", "🌨️"),
            73: ("Snow", "❄️"),
            75: ("Heavy snow", "❄️"),
            95: ("Thunderstorm", "⛈️"),
        }

        return mapping.get(code, ("Unknown", "🌍"))

