@echo off
setlocal
set "ROOT=%~dp0"
"%ROOT%.venv\Scripts\python.exe" "%ROOT%src\main_window.py"
