# TrayWeatherApp module: workers.py
from datetime import datetime, timezone, timedelta
from PyQt6.QtCore import QObject, pyqtSignal
from TrayWeatherApp.weather_cache import valid_weather
from TrayWeatherApp.forecast import parse_daily
import requests

# ---------- Weather Worker ----------
class WeatherWorker(QObject):
    finished = pyqtSignal(str, object)
    error = pyqtSignal(str, str)
    result = pyqtSignal(str, object)
    done = pyqtSignal()

    def __init__(self, city: str, units: str, location=None, request_id=None):
        super().__init__()
        self.city = city
        self.units = units
        self.location = location
        self.request_id = request_id

    def run(self):
        try:
            loc = self.location
            if not loc:
                rg = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                                  params={"name": self.city, "count": 1}, timeout=10)
                if rg.status_code != 200:
                    raise ValueError(f"Geocode error {rg.status_code}")
                geo = rg.json().get("results", [])
                if not geo:
                    raise ValueError(f"City not found: {self.city}")
                loc = geo[0]
            lat, lon = loc["latitude"], loc["longitude"]
            display_name = location_label(loc)

            if self.thread().isInterruptionRequested():
                return

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
                "daily": ["temperature_2m_max", "temperature_2m_min", "weather_code", "precipitation_probability_max"],
                "forecast_days": 5,
                "timezone": "auto",
                "temperature_unit": temp_unit,
                "wind_speed_unit": wind_unit,
            }

            r = requests.get(url, params=params, timeout=10)
            if r.status_code != 200:
                raise ValueError(f"Weather API error {r.status_code}")
            if self.thread().isInterruptionRequested():
                return
            d = r.json()
            cur, daily = d.get("current", {}), d.get("daily", {})

            tz_offset = d.get("utc_offset_seconds", 0)
            local_time = datetime.now(timezone.utc) + timedelta(seconds=tz_offset)
            hour = local_time.hour
            is_night = hour < 6 or hour >= 18

            desc, emoji = self.map_weather_code(cur.get("weather_code"), is_night=is_night)

            info = {
                "city": display_name,
                "location": loc,
                "units": self.units,
                "request_id": self.request_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "temp": cur.get("temperature_2m"),
                "feels_like": cur.get("apparent_temperature"),
                "humidity": cur.get("relative_humidity_2m"),
                "wind_speed": cur.get("wind_speed_10m"),
                "desc": desc,
                "icon": emoji,
                "timezone": tz_offset,
                "high": (daily.get("temperature_2m_max") or [None])[0],
                "low": (daily.get("temperature_2m_min") or [None])[0],
                "forecast": parse_daily(daily, self.map_weather_code),
            }
            if not valid_weather(info):
                raise ValueError("Weather API returned no valid current temperature.")
            self.finished.emit(self.city, info)
            self.result.emit(self.city, info)

        except Exception as e:
            self.error.emit(self.city, str(e))
            self.result.emit(self.city, {"error": str(e), "units": self.units,
                                         "request_id": self.request_id})
        finally:
            self.done.emit()

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
            56: ("Light freezing drizzle", "🌧️"),
            57: ("Freezing drizzle", "🌧️"),
            66: ("Light freezing rain", "🌧️"),
            67: ("Freezing rain", "🌧️"),
            77: ("Snow grains", "🌨️"),
            80: ("Light showers", "🌦️"),
            81: ("Showers", "🌧️"),
            82: ("Heavy showers", "🌧️"),
            85: ("Light snow showers", "🌨️"),
            86: ("Snow showers", "❄️"),
            95: ("Thunderstorm", "⛈️"),
            96: ("Thunderstorm with hail", "⛈️"),
            99: ("Thunderstorm with heavy hail", "⛈️"),
        }

        return mapping.get(code, ("Unknown", "🌍"))



def location_label(location):
    parts = [location.get("name", ""), location.get("admin1", ""),
             location.get("country", "") or location.get("country_code", "")]
    return ", ".join(dict.fromkeys(p for p in parts if p))


def search_locations(query):
    response = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                            params={"name": query.strip(), "count": 10, "language": "en"},
                            timeout=10)
    response.raise_for_status()
    results = response.json().get("results", [])
    return [loc for loc in results if isinstance(loc, dict)
            and isinstance(loc.get("latitude"), (int, float))
            and isinstance(loc.get("longitude"), (int, float))
            and loc.get("name")]
