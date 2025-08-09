@echo off
REM Windows batch script to start Trade Analyst application

echo Starting Trade Analyst Application...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Install dependencies if requirements.txt is newer than last install
if not exist ".last_install" goto install_deps
for /f %%i in ('forfiles /m requirements.txt /c "cmd /c echo @fdate @ftime" 2^>nul') do set req_time=%%i
for /f %%i in ('forfiles /m .last_install /c "cmd /c echo @fdate @ftime" 2^>nul') do set install_time=%%i
if "%req_time%" neq "%install_time%" goto install_deps
goto start_app

:install_deps
echo Installing/updating dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)
echo. > .last_install

:start_app
REM Start the application
echo.
echo Starting Trade Analyst...
echo Press Ctrl+C to stop the application
echo.

python start.py server %*

REM Deactivate virtual environment
deactivate

echo.
echo Trade Analyst stopped.
pause
