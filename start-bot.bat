@echo off
rem Starts the Daily Red bot. Used by Task Scheduler; you can also double-click it.
cd /d "%~dp0"
".venv\Scripts\python.exe" bot.py >> bot.log 2>&1
