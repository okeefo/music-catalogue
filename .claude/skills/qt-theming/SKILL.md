---
name: qt-theming
description: How theming works in this app — use whenever styling any widget, changing colours, adding a theme, or building new UI. Covers the ThemeManager architecture, palette tokens, and the rules that keep every theme working.
---

# Qt Theming in Music Catalogue

All colours come from **named themes**. Never hardcode a colour in a widget,
a .ui file, or a `setStyleSheet()` call — every colour flows through the theme
system or it will break when the user switches themes.

## Architecture

- `src/ui/theme_manager.py` — `ThemeManager` (QObject singleton).
  - `apply(name, persist=False)` renders the template with a palette and sets it
    on the whole QApplication. `persist=True` saves to `config.ini [ui] theme`.
  - `apply_saved_theme()` — called once at startup by `main_window.py`.
  - `color(token, fallback)` → `QColor` for custom-painted widgets.
  - `themeChanged(str)` signal — connect anything that caches colours.
- `src/qt/themes/base.qss.template` — the single master stylesheet. Placeholders
  are `@token-name`; ThemeManager substitutes them from the active palette.
- `src/qt/themes/<name>.json` — one palette per theme:
  `{"display_name": "...", "colors": {"token": "#RRGGBB", ...}}`.
  Current themes: `slate` (the original grey-green look, default), `dark`,
  `light`, `midnight`.

## Switching UI (already wired — don't duplicate)

- View: Options menu → Theme submenu (checkable, exclusive) in `main_window.py`
  `__setup_theme_menu`.
- Settings dialog: Appearance → Theme combo (`theme_combo` in `settings.ui`),
  applied+persisted on OK.

## Rules

1. **Styling a regular widget**: add/extend a rule in `base.qss.template` using
   existing tokens. Only invent a new token when no existing one fits.
2. **New token**: add it to **every** palette JSON in `src/qt/themes/`. A missing
   token renders magenta and logs an error — that's the tell.
3. **Custom-painted widgets** (paintEvent): fetch colours at paint time via
   `ThemeManager().color("token", "fallback")` — do not cache QColors at
   construction. See `custom_waveform_widget.py` and `waveform_editor_dialog.py`
   (tokens: `waveform-bg/-played/-unplayed/-needle`, `editor-selection/-edge`).
4. **Dynamic stylesheets in Python** (rare; e.g. the ID3 tag labels in
   `main_window.__setup_label_style_sheet`): build the string from
   `ThemeManager().color(...).name()` and re-run the setup on `themeChanged`.
5. **Never** add a `styleSheet` property in a `.ui` file — inline styles override
   the application stylesheet and are invisible to themes. They were all
   deliberately stripped.
6. Widget-specific styling in the template targets `objectName` selectors
   (e.g. `#frame_left_menu`), not new inline styles.

## Adding a theme

1. Copy an existing palette JSON in `src/qt/themes/` to `<newname>.json`.
2. Change `display_name` and the colour values (keep **all** tokens).
3. Done — ThemeManager discovers palettes by scanning the directory; the menu
   and Settings combo pick it up automatically.

## Verifying theme changes

Render every theme offscreen and eyeball the PNGs:

```bash
cd src && QT_QPA_PLATFORM=offscreen python -c "
import sys, os
from PyQt5.QtWidgets import QApplication
from PyQt5 import uic
app = QApplication(sys.argv)
import qt.resources_rcc
from ui.theme_manager import ThemeManager
w = uic.loadUi('qt/music_manager.ui'); w.resize(1400, 900)
tm = ThemeManager()
for name in tm.available_themes():
    tm.apply(name); app.processEvents()
    w.grab().save(f'theme-{name}.png')
"
```

Watch the log for `Theme '<x>' is missing tokens: [...]` — that means a palette
needs updating (offending areas render magenta).
