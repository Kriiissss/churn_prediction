@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
echo ========================================
echo ЛР: поднять MinIO (docker compose)
echo ========================================
docker compose up -d
if errorlevel 1 (
    echo ОШИБКА: docker compose
    exit /b 1
)
echo Готово. Консоль MinIO: http://localhost:9001
exit /b 0
