@echo off
REM Visual A4 comparison: HTML print PDF vs Typst PDF
cd /d "%~dp0.."
python tools\compare_html_typst.py %*
exit /b %ERRORLEVEL%
