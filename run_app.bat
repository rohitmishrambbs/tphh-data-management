@echo off
title TPHH Data Management System
cd /d "%~dp0"
echo ================================================================
echo           TPHH Data Management System (Local Portal)
echo ================================================================
echo.
echo Starting the high-speed engine and opening your web browser...
echo.
echo If your browser does not open automatically, visit:
echo http://localhost:8501
echo.
echo (Keep this window open while using the application)
echo (Press Ctrl+C or close this window when you want to exit)
echo ================================================================
echo.
start http://localhost:8501
python -m streamlit run app.py --server.headless false --browser.gatherUsageStats false
pause
