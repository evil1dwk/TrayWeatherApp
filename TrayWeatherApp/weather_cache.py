"""Small, atomic cache of successful weather responses, separated by location and units."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

CACHE_PATH = Path.home() / ".TrayWeatherApp" / "weather-cache.json"


def parse_timestamp(value):
    try:
        value = datetime.fromisoformat(value)
        return value.astimezone(timezone.utc) if value.tzinfo else None
    except (TypeError, ValueError):
        return None


def valid_weather(info):
    return (isinstance(info, dict)
            and isinstance(info.get("temp"), (int, float))
            and not isinstance(info.get("temp"), bool)
            and math.isfinite(info["temp"])
            and parse_timestamp(info.get("updated_at")) is not None)


class WeatherCache:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else CACHE_PATH
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.entries = ({key: info for key, info in data.items() if valid_weather(info)}
                            if isinstance(data, dict) else {})
        except (OSError, ValueError):
            self.entries = {}

    @staticmethod
    def key(city, units, location=None):
        identity = [city, units]
        if location:
            identity += [location.get("latitude"), location.get("longitude")]
        return hashlib.sha256(json.dumps(identity).encode()).hexdigest()

    def get(self, city, units, location=None):
        info = self.entries.get(self.key(city, units, location))
        return deepcopy(info) if valid_weather(info) and info.get("units") == units else None

    def put(self, city, units, info, location=None):
        if not valid_weather(info) or info.get("units") != units:
            return
        self.entries[self.key(city, units, location)] = deepcopy(info)
        # Keep the cache bounded even after many removed cities.
        self.entries = dict(sorted(self.entries.items(), key=lambda item: item[1].get("updated_at", "")
                                   if isinstance(item[1], dict) else "")[-200:])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile("w", dir=self.path.parent, delete=False,
                                             encoding="utf-8") as stream:
                temporary = Path(stream.name)
                json.dump(self.entries, stream, allow_nan=False)
            os.replace(temporary, self.path)
        finally:
            if temporary and temporary.exists():
                temporary.unlink()
