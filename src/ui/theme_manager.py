import json
import os
import re

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication

from config_manager import ConfigurationManager
from log_config import get_logger

logger = get_logger(__name__)

_THEMES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "qt", "themes")
_TEMPLATE_FILE = os.path.join(_THEMES_DIR, "base.qss.template")

DEFAULT_THEME = "slate"


class ThemeManager(QObject):
    """Singleton that applies named colour themes to the whole application.

    Each theme is a JSON palette in src/qt/themes/ that fills the @tokens in
    base.qss.template; the rendered stylesheet is set on the QApplication.
    Custom-painted widgets read their colours via color() and repaint on the
    themeChanged signal.
    """

    themeChanged = pyqtSignal(str)

    _instance = None

    def __new__(cls):
        if not isinstance(cls._instance, cls):
            cls._instance = super().__new__(cls)
            cls._instance.__initialised = False
        return cls._instance

    def __init__(self):
        if self.__initialised:
            return
        super().__init__()
        self.__initialised = True
        self._palettes = {}
        self._current = None
        self.__load_palettes()

    def __load_palettes(self) -> None:
        for filename in sorted(os.listdir(_THEMES_DIR)):
            if not filename.endswith(".json"):
                continue
            name = os.path.splitext(filename)[0]
            try:
                with open(os.path.join(_THEMES_DIR, filename), encoding="utf-8") as f:
                    self._palettes[name] = json.load(f)
            except Exception:
                logger.exception(f"Failed to load theme palette: {filename}")
        logger.info(f"Loaded themes: {list(self._palettes)}")

    def available_themes(self) -> dict:
        """Return {theme_name: display_name} for all loadable palettes."""
        return {name: p.get("display_name", name.title()) for name, p in self._palettes.items()}

    @property
    def current_theme(self) -> str:
        return self._current or DEFAULT_THEME

    def apply_saved_theme(self) -> None:
        """Apply the theme stored in config.ini (or the default). Call once at startup."""
        saved = ConfigurationManager().get("ui", "theme", fallback=DEFAULT_THEME)
        self.apply(saved if saved in self._palettes else DEFAULT_THEME)

    def apply(self, name: str, persist: bool = False) -> None:
        """Render the template with the named palette and set it on the application."""
        palette = self._palettes.get(name)
        if palette is None:
            logger.error(f"Unknown theme '{name}'; keeping current theme")
            return

        with open(_TEMPLATE_FILE, encoding="utf-8") as f:
            template = f.read()

        colors = palette["colors"]
        missing = set()

        def substitute(match):
            token = match.group(1)
            if token in colors:
                return colors[token]
            missing.add(token)
            return "magenta"  # unmissable in the UI and harmless

        qss = re.sub(r"@([\w-]+)", substitute, template)
        if missing:
            logger.error(f"Theme '{name}' is missing tokens: {sorted(missing)}")

        QApplication.instance().setStyleSheet(qss)
        self._current = name
        logger.info(f"Applied theme: {name}")

        if persist:
            cfg = ConfigurationManager()
            cfg.set("ui", "theme", name)
            cfg.save()

        self.themeChanged.emit(name)

    def color(self, token: str, fallback: str = "magenta") -> QColor:
        """Colour for custom-painted widgets, from the current theme's palette."""
        palette = self._palettes.get(self.current_theme, {})
        return QColor(palette.get("colors", {}).get(token, fallback))
