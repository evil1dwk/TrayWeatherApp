"""Validated JSON themes with read-only presets and portable ZIP compatibility."""
import json
from pathlib import Path
import re
import zipfile
import zlib

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication
from TrayWeatherApp.config_utils import BASE_DIR, log

BUILTIN_DIR = Path(__file__).resolve().parent / "themes"
THEMES_DIR = Path.home() / ".TrayWeatherApp" / "themes"
MAX_THEME_BYTES = 1024 * 1024
DEFAULTS = {
    "schema_version": 1, "name": "Dark",
    "background_gradient": ["#12141A", "#1A2036"],
    "glass_card_color": "rgba(20,22,30,150)",
    "card_border_color": "rgba(255,255,255,25)",
    "text_primary": "#E6E8EE", "text_muted": "#9EA3B8",
    "text_desc": "#C5C9D3", "text_more": "#A8AFC2",
    "temp_color": "#FFD18A", "high_color": "#FFB347", "low_color": "#7DD3FC",
    "humid_color": "#7DD3FC", "wind_color": "#C4B5FD", "accent_glow": "#FFC878",
    "link_color": "#7DD3FC", "tab_bg": "rgba(255,255,255,0.10)",
    "tab_bg_selected": "rgba(255,255,255,0.18)", "tab_text": "#E6E8EE",
    "tab_border": "rgba(255,255,255,0.25)",
}
COLOR_KEYS = set(DEFAULTS) - {"schema_version", "name", "background_gradient"}


class ThemeError(ValueError):
    """A theme could not be read or validated."""


class ThemeManager(QObject):
    changed = pyqtSignal()

    def __init__(self, custom_dir=None, builtin_dir=None, legacy_dirs=None):
        super().__init__()
        self.custom_dir = Path(custom_dir) if custom_dir is not None else THEMES_DIR
        self.builtin_dir = Path(builtin_dir) if builtin_dir is not None else BUILTIN_DIR
        self.legacy_dirs = ([BASE_DIR / "themes"] if legacy_dirs is None
                            else [Path(p) for p in legacy_dirs])
        self.current_name = "System"
        self.current_json = dict(DEFAULTS)
        self.current_css = ""
        self.last_error = None
        self._app = None
        self._watching = False
        self.load_theme("System")

    @staticmethod
    def _color(value):
        if not isinstance(value, str):
            raise ThemeError("Colors must be strings.")
        match = re.fullmatch(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+(?:\.\d+)?)\s*\)", value)
        if match:
            r, g, b = map(int, match.groups()[:3])
            alpha = float(match[4])
            if max(r, g, b) > 255 or alpha > 255:
                raise ThemeError(f"Invalid color: {value}")
            return QColor(r, g, b, round(alpha * 255 if alpha <= 1 else alpha))
        color = QColor(value)
        if not color.isValid():
            raise ThemeError(f"Invalid color: {value}")
        return color

    @staticmethod
    def parse_color(value, default="#000000"):
        try:
            return ThemeManager._color(value)
        except ThemeError:
            return ThemeManager._color(default)

    @classmethod
    def validate(cls, data):
        if not isinstance(data, dict):
            raise ThemeError("Theme JSON must be an object.")
        if type(data.get("schema_version", 1)) is not int or data.get("schema_version", 1) != 1:
            raise ThemeError("Unsupported theme schema_version; expected 1.")
        name = data.get("name", "Custom")
        if not isinstance(name, str) or not name.strip() or len(name) > 80:
            raise ThemeError("Theme name must contain 1–80 characters.")
        result = {**DEFAULTS, **data, "name": name.strip()}
        gradient = result["background_gradient"]
        if not isinstance(gradient, list) or len(gradient) != 2:
            raise ThemeError("background_gradient must contain two colors.")
        for key in COLOR_KEYS:
            try:
                cls._color(result[key])
            except ThemeError as exc:
                raise ThemeError(f"{key}: {exc}") from exc
        result["background_gradient"] = [cls._color(color).name() for color in gradient]
        css = result.get("css", "")
        if not isinstance(css, str):
            raise ThemeError("Optional css must be text.")
        return result

    @classmethod
    def read_theme(cls, path):
        path = Path(path)
        try:
            if path.suffix.lower() == ".zip":
                with zipfile.ZipFile(path) as archive:
                    jsons = [p for p in archive.infolist() if p.filename.lower().endswith(".json")]
                    css = [p for p in archive.infolist() if p.filename.lower().endswith(".css")]
                    if len(jsons) != 1 or len(css) > 1:
                        raise ThemeError("Theme ZIP must contain one JSON file and at most one CSS file.")
                    if sum(p.file_size for p in jsons + css) > MAX_THEME_BYTES:
                        raise ThemeError("Theme contents exceed 1 MiB.")
                    data = json.loads(archive.read(jsons[0]).decode("utf-8"))
                    if css and isinstance(data, dict):
                        data["css"] = archive.read(css[0]).decode("utf-8")
            else:
                if path.stat().st_size > MAX_THEME_BYTES:
                    raise ThemeError("Theme exceeds 1 MiB.")
                data = json.loads(path.read_text(encoding="utf-8"))
            return cls.validate(data)
        except (OSError, ValueError, UnicodeError, zipfile.BadZipFile, RuntimeError, EOFError, zlib.error) as exc:
            raise ThemeError(f"{path.name}: {exc}") from exc

    def catalog(self):
        # Reserved presets always retain their identity; imported copies are renamed.
        catalog = {}
        for directory in [self.builtin_dir, *self.legacy_dirs, self.custom_dir]:
            for path in sorted(directory.glob("*")):
                if path.suffix.lower() not in (".json", ".zip"):
                    continue
                if path.stem.casefold() == "system":
                    suffix = "custom" if directory == self.custom_dir else "legacy"
                    catalog[f"{path.stem} ({suffix})"] = path
                    continue
                existing = next((n for n in catalog if n.casefold() == path.stem.casefold()), None)
                if existing is not None:
                    if directory == self.custom_dir and path != catalog[existing]:
                        catalog[f"{path.stem} (custom)"] = path
                    continue
                catalog[path.stem] = path
        return catalog

    def list_themes(self):
        return ["System"] + sorted(self.catalog(), key=str.casefold)

    def _system_preset(self):
        app = QApplication.instance()
        hints = app.styleHints() if app else None
        scheme = hints.colorScheme() if hints and hasattr(hints, "colorScheme") else None
        light = getattr(getattr(Qt, "ColorScheme", None), "Light", object())
        return "Light" if scheme == light else "Dark"

    def load_theme(self, name):
        catalog = self.catalog()
        selected = next((n for n in ["System", *catalog] if n.casefold() == str(name).casefold()), name)
        target = self._system_preset() if selected == "System" else selected
        if target not in catalog:
            raise FileNotFoundError(f"Theme not found: {name}")
        data = self.read_theme(catalog[target])
        self.current_name = selected
        self.current_json = data
        self.current_css = self.stylesheet()
        self.last_error = None

    def select_theme(self, name):
        """Apply a theme, retaining a usable built-in fallback if a file is bad."""
        try:
            self.load_theme(name)
        except (ThemeError, FileNotFoundError) as exc:
            self.last_error = str(exc)
            log(f"Theme fallback: {exc}", "ERROR")
            error = self.last_error
            self.load_theme("Dark")
            self.last_error = error
        if self._app is not None:
            self.apply_to_app(self._app)
        self.changed.emit()

    def stylesheet(self):
        d = self.current_json
        bg = self.parse_color(d["background_gradient"][0]).name()
        text = self.parse_color(d["text_primary"]).name()
        accent = self.parse_color(d["link_color"]).name()
        border = self.parse_color(d["card_border_color"]).name(QColor.NameFormat.HexArgb)
        return f"""
QWidget {{ color: {text}; font-family: "Segoe UI", "Helvetica Neue", Arial; }}
QDialog, QMenu, QMessageBox {{ background: {bg}; }}
QMenu::item {{ padding: 8px 16px; }}
QMenu::item:selected {{ background: {accent}; color: {bg}; }}
QLineEdit, QComboBox, QComboBox QAbstractItemView {{
    background: {bg}; color: {text}; border: 1px solid {border};
    border-radius: 6px; padding: 5px;
}}
QComboBox QAbstractItemView {{ selection-background-color: {accent}; }}
QPushButton {{ background: {bg}; color: {text}; border: 1px solid {accent};
    border-radius: 6px; padding: 6px 12px; }}
QPushButton:hover {{ border: 2px solid {accent}; }}
QCheckBox {{ spacing: 8px; }}
""" + d.get("css", "")

    def apply_to_app(self, app):
        self._app = app
        app.setStyleSheet(self.stylesheet())
        palette = app.palette()
        for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
            palette.setColor(role, self.parse_color(self.value("text_primary")))
        for role in (QPalette.ColorRole.Window, QPalette.ColorRole.Base, QPalette.ColorRole.Button):
            palette.setColor(role, self.parse_color(self.value("background_gradient")[0]))
        palette.setColor(QPalette.ColorRole.Link, self.parse_color(self.value("link_color")))
        palette.setColor(QPalette.ColorRole.LinkVisited, self.parse_color(self.value("link_color")))
        app.setPalette(palette)
        hints = app.styleHints()
        if not self._watching and hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(self._system_changed)
            self._watching = True

    def _system_changed(self, *_):
        if self.current_name == "System":
            self.select_theme("System")

    def import_theme(self, source):
        data = self.read_theme(source)
        stem = re.sub(r"[^\w .-]", "_", data["name"]).strip(" .")[:70] or "Custom"
        self.custom_dir.mkdir(parents=True, exist_ok=True)
        existing = {n.casefold() for n in self.list_themes()}
        name = stem
        number = 1
        while name.casefold() in existing or (self.custom_dir / f"{name}.json").exists():
            name = f"{stem} ({number})"
            number += 1
        data["name"] = name
        path = self.custom_dir / f"{name}.json"
        with path.open("x", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
        return name

    def export_theme(self, name, destination):
        preview = ThemeManager(self.custom_dir, self.builtin_dir, self.legacy_dirs)
        preview.load_theme(name)
        data = {**preview.current_json, "name": preview.current_json["name"]}
        Path(destination).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def value(self, key, default=None):
        return self.current_json.get(key, default)
