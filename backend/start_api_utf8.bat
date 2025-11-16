@echo off
REM Start API Server with UTF-8 encoding support
REM This fixes emoji display issues on Windows

echo Starting HiddenGem API Server with UTF-8 encoding...
echo.

REM Set environment to use UTF-8
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
chcp 65001 >nul

REM Activate conda environment
call C:\ProgramData\miniconda3\condabin\conda.bat activate hiddengem_gpu

REM Check if environment is activated
if errorlevel 1 (
    echo Error: Failed to activate conda environment 'hiddengem_gpu'
    echo Please check if the environment exists: conda env list
    pause
    exit /b 1
)

echo Environment activated: %CONDA_DEFAULT_ENV%
echo.

REM Start API server
echo Starting uvicorn server...
python -m uvicorn api.main:app --host 192.168.31.147 --port 8000

if errorlevel 1 (
    echo.
    echo Error: Failed to start API server
    pause
    exit /b 1
)
