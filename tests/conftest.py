"""
conftest.py — project-wide pytest fixtures and import-time patches.

The src/ modules are imported while sys.path already contains 'src/'
(configured via [tool.pytest.ini_options] pythonpath in pyproject.toml).

Several src/ modules have import-time side-effects that fail outside of the
full application environment (log_config reads config.ini, audio_tags
instantiates AudioTagHelper at module level, PyQt5 may not be installed in
the test Python environment, etc.).  We patch those before any test module
triggers the real imports.
"""

import sys
import logging
import types
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Stub out PyQt5 so that src modules importing it don't fail when PyQt5 is
# not installed in the current Python environment (e.g. a system Python
# running against a Windows venv that holds the real Qt packages).
# We use real integer constants that match the actual QMessageBox values so
# any comparison logic in the module under test still works.
# ---------------------------------------------------------------------------
_qmsgbox_mock = MagicMock()
# QMessageBox button return values (standard Qt5 values)
_qmsgbox_mock.Yes = 16384
_qmsgbox_mock.No = 65536
_qmsgbox_mock.YesToAll = 32768
_qmsgbox_mock.NoToAll = 131072
_qmsgbox_mock.Cancel = 4194304

_qtwidgets_mock = MagicMock()
_qtwidgets_mock.QMessageBox = _qmsgbox_mock
_qtwidgets_mock.QApplication = MagicMock()

_pyqt5_mock = MagicMock()
_pyqt5_mock.QtWidgets = _qtwidgets_mock

sys.modules.setdefault("PyQt5", _pyqt5_mock)
sys.modules.setdefault("PyQt5.QtWidgets", _qtwidgets_mock)
sys.modules.setdefault("PyQt5.QtCore", MagicMock())
sys.modules.setdefault("PyQt5.QtGui", MagicMock())


# ---------------------------------------------------------------------------
# Provide a lightweight log_config stub so that importing any src/ module
# that calls `from log_config import get_logger` does NOT attempt to read
# config.ini from disk.
# ---------------------------------------------------------------------------
_log_config_stub = types.ModuleType("log_config")
_log_config_stub.get_logger = lambda name: logging.getLogger(name)
sys.modules.setdefault("log_config", _log_config_stub)


# ---------------------------------------------------------------------------
# Provide a stub for path_helper so log_config (if imported directly) doesn't
# fail looking for helper functions.
# ---------------------------------------------------------------------------
_path_helper_stub = types.ModuleType("path_helper")
_path_helper_stub.get_absolute_path_log_dir = lambda: "/tmp"
_path_helper_stub.get_absolute_path_config = lambda: "config.ini"
sys.modules.setdefault("path_helper", _path_helper_stub)


# ---------------------------------------------------------------------------
# Stub ui.custom_messagebox so the module-level import in repackage_dir
# doesn't fail (the function is only called when a real dialog is needed,
# which is never triggered in unit tests).
# ---------------------------------------------------------------------------
_ui_pkg = types.ModuleType("ui")
_custom_mb = types.ModuleType("ui.custom_messagebox")

class _ButtonType:
    YesNo = 0
    YesNoCancel = 1
    YesNoToAllCancel = 2

_custom_mb.ButtonType = _ButtonType
_custom_mb.show_message_box = MagicMock(return_value=0)
_custom_mb.convert_response_to_string = lambda r: str(r)

sys.modules.setdefault("ui", _ui_pkg)
sys.modules.setdefault("ui.custom_messagebox", _custom_mb)


# ---------------------------------------------------------------------------
# Stub taglib so AudioTagHelper can be imported without the native extension.
# ---------------------------------------------------------------------------
_taglib_mock = MagicMock()
sys.modules.setdefault("taglib", _taglib_mock)


# ---------------------------------------------------------------------------
# Stub mutagen sub-modules used by audio_tags at import time.
# ---------------------------------------------------------------------------
for _mod in ("mutagen", "mutagen.wave", "mutagen.id3", "mutagen.flac", "mutagen.mp3"):
    sys.modules.setdefault(_mod, MagicMock())


# ---------------------------------------------------------------------------
# Stub discogs_client and discogs_client.models so modules that import them
# (e.g. file_operations/auto_tag.py) can be loaded without the real package.
# We expose lightweight placeholder classes for Release and Track so that
# Pydantic's arbitrary_types_allowed check in ReleaseFacade can resolve the
# annotation without errors.
# ---------------------------------------------------------------------------
import types as _types  # noqa: E402 (already imported above as 'types')

class _FakeDiscogsRelease:
    """Minimal stand-in for discogs_client.models.Release."""

class _FakeDiscogsTrack:
    """Minimal stand-in for discogs_client.models.Track."""

_discogs_models_stub = _types.ModuleType("discogs_client.models")
_discogs_models_stub.Release = _FakeDiscogsRelease
_discogs_models_stub.Track = _FakeDiscogsTrack

_discogs_client_stub = MagicMock()
_discogs_client_stub.models = _discogs_models_stub

sys.modules.setdefault("discogs_client", _discogs_client_stub)
sys.modules.setdefault("discogs_client.models", _discogs_models_stub)

# requests is used at module level by auto_tag (header dict only); stub it.
sys.modules.setdefault("requests", MagicMock())

# ui.progress_bar_helper is imported at module level by auto_tag.
_ui_pbh_stub = _types.ModuleType("ui.progress_bar_helper")
_ui_pbh_stub.ProgressBarHelper = MagicMock()
sys.modules.setdefault("ui.progress_bar_helper", _ui_pbh_stub)

# config_manager is imported at module level by auto_tag.
_cfg_mgr_stub = _types.ModuleType("config_manager")
_cfg_mgr_stub.ConfigurationManager = MagicMock()
sys.modules.setdefault("config_manager", _cfg_mgr_stub)
