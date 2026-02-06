$root = Split-Path -Parent $PSCommandPath
& "$root\.venv\Scripts\python.exe" "$root\src\main_window.py"
