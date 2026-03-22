@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
echo ========================================
echo ЛР: DVC — зафиксировать корпус и отправить в MinIO (dvc push)
echo ========================================
if not exist "data\corpus\en\" (
    echo ОШИБКА: нет data\corpus. Сначала: scripts\lab_generate_corpus.bat
    exit /b 1
)
echo.
echo ^> poetry run dvc add data/corpus
poetry run dvc add data/corpus
if errorlevel 1 (
    echo ОШИБКА: dvc add
    exit /b 1
)
echo.
echo ^> poetry run dvc push
poetry run dvc push
if errorlevel 1 (
    echo ОШИБКА: dvc push — проверьте MinIO, учётные данные для S3 remote, .dvc\config
    exit /b 1
)
echo.
echo Готово. Метаданные: data\corpus.dvc, данные — в remote MinIO.
exit /b 0
