@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
echo ========================================
echo ЛР: версионирование — dvc status
echo ========================================
poetry run dvc status
exit /b %ERRORLEVEL%
