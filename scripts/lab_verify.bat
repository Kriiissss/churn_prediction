@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
echo ========================================
echo ЛР: автопроверка (.env, MinIO, корпус, детектор, DVC)
echo ========================================
poetry run python scripts/lab_verify.py
exit /b %ERRORLEVEL%
