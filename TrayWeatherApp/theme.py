# TrayWeatherApp module: theme.py

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication
from TrayWeatherApp.config_utils import THEMES_DIR
import re, zipfile, json, io, colorsys

# ---------- Theme Manager ----------
class ThemeManager:
    def __init__(self):
        self.current_name = None
        self.current_css = ""
        self.current_json = {}
        self.cache = {}

    def list_themes(self):
        names = []
        for z in THEMES_DIR.glob("*.zip"):
            names.append(z.stem)
        return sorted(names)

    def load_theme(self, name: str):
        if name in self.cache:
            self.current_name = name
            self.current_css, self.current_json = self.cache[name]
            return

        zip_path = THEMES_DIR / f"{name}.zip"
        if not zip_path.exists():
            raise FileNotFoundError(f"Theme ZIP not found: {zip_path}")

        with zip_path.open("rb") as f:
            data = f.read()
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            css_name = None
            json_name = None
            for n in zf.namelist():
                if n.lower().endswith(".css"): css_name = n
                if n.lower().endswith(".json"): json_name = n
            if not css_name or not json_name:
                raise ValueError("Theme zip must contain one .css and one .json")

            css_bytes = zf.read(css_name)
            json_bytes = zf.read(json_name)

        css_text = css_bytes.decode("utf-8")
        json_text = json_bytes.decode("utf-8")
        try:
            json_obj = json.loads(json_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in theme '{name}': {e}") from e

        self.cache[name] = (css_text, json_obj)
        self.current_name = name
        self.current_css = css_text
        self.current_json = json_obj

    def _luminance(self, hex_color: str) -> float:
        qc = QColor(hex_color)
        r, g, b = qc.redF(), qc.greenF(), qc.blueF()
        return colorsys.rgb_to_hls(r, g, b)[1]

    def _auto_link_color(self) -> str:
        link = self.value("link_color", "#7DD3FC")
        bg = self.value("background_gradient", ["#12141A", "#1A2036"])
        bg_hex = bg[0] if isinstance(bg, list) and bg else "#12141A"
        brightness = self._luminance(bg_hex)
        if brightness > 0.6:
            return "#0A3D62"
        else:
            return "#7DD3FC"

    def apply_to_app(self, app: QApplication):
        app.setStyleSheet(self.current_css or "")

        pal = app.palette()

        text_hex = self.value("text_primary", "#E6E8EE")
        link_hex = self._auto_link_color()

        pal.setColor(QPalette.ColorRole.WindowText, QColor(text_hex))
        pal.setColor(QPalette.ColorRole.Text, QColor(text_hex))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor(text_hex))
        pal.setColor(QPalette.ColorRole.Link, QColor(link_hex))
        pal.setColor(QPalette.ColorRole.LinkVisited, QColor(link_hex))

        app.setPalette(pal)

    @staticmethod
    def parse_color(value: str, default: str = "#000000") -> QColor:
        if not isinstance(value, str):
            return QColor(default)
        s = value.strip()
        if s.startswith("rgba"):
            m = re.match(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)", s)
            if m:
                r, g, b, a = m.groups()
                a_val = float(a)
                if a_val <= 1:
                    a_val = a_val * 255
                return QColor(int(r), int(g), int(b), int(a_val))
        try:
            return QColor(s)
        except Exception:
            return QColor(default)

    def value(self, key: str, default=None):
        return self.current_json.get(key, default)
