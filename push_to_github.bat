@echo off
title Push TPHH Project to GitHub
cd /d "%~dp0"
echo ================================================================
echo         Pushing TPHH Project to your GitHub Account
echo ================================================================
echo.
echo 1. Setting up remote repository link...
git remote remove origin 2>nul
git remote add origin https://github.com/rohitmishrambbs/tphh-data-management.git
git branch -M main
echo 2. Pushing files to GitHub...
echo (If a browser window appears, click "Sign in with browser" to authorize)
echo.
git push -u origin main
echo.
echo ================================================================
echo Done! Now open https://share.streamlit.io to launch your app.
echo ================================================================
pause

