@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
echo ========================================
echo ЛР: pytest (покрытие src 100%%)
echo ========================================
poetry run pytest -q
exit /b %ERRORLEVEL%
