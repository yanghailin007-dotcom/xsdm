@echo off
chcp 65001 >nul
echo Starting page monitor...
echo This will run continuously and check pages every 5 minutes
echo Log will be saved to: logs\page_monitor.log
echo.
echo Press Ctrl+C to stop
echo.
python monitor_pages.py
pause
