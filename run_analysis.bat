@echo off
cd /d "%~dp0"
py -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
py -m unittest discover -s tests -v
if errorlevel 1 exit /b 1
py src\analysis.py
if errorlevel 1 exit /b 1
echo Analysis completed. See results\ and figures\.
pause
