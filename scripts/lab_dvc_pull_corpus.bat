@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
echo ========================================
echo ЛР: синхронизация — скачать корпус с MinIO (dvc pull)
echo ========================================
poetry run dvc pull
if errorlevel 1 (
    echo ОШИБКА: dvc pull
    exit /b 1
)
echo Готово.
exit /b 0
