@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

echo.
echo ============================================================
echo   Настройка и проверка лабораторной (один сценарий)
echo ============================================================
echo.

echo [1/7] Docker Compose: MinIO и бакет datasets
docker compose up -d
if errorlevel 1 (
    echo ОШИБКА: docker compose. Установите Docker Desktop и повторите.
    exit /b 1
)
echo Ожидание 10 сек...
timeout /t 10 /nobreak >nul
echo.

echo [2/7] DVC: попытка подтянуть данные с remote (если уже есть в MinIO)
poetry run dvc pull
if errorlevel 1 (
    echo [ВНИМАНИЕ] dvc pull не удался — возможен первый запуск без remote.
)
echo.

echo [3/7] Корпус: если нет — генерация (generate_corpus_data)
call "%~dp0lab_ensure_corpus.bat"
if errorlevel 1 (
    echo ОШИБКА: генерация корпуса.
    exit /b 1
)
echo.

echo [4/7] DVC: зафиксировать корпус и отправить в MinIO
poetry run dvc add data/corpus
if errorlevel 1 (
    echo ОШИБКА: dvc add data/corpus
    exit /b 1
)
poetry run dvc push
if errorlevel 1 (
    echo ОШИБКА: dvc push — проверьте MinIO, remote и .dvc\config.local (см. README^).
    exit /b 1
)
echo.

echo [5/7] Демонстрация: удалить локальный каталог data\corpus и восстановить через DVC
if exist data\corpus (
    rmdir /s /q data\corpus
    echo Каталог data\corpus удалён.
) else (
    echo Папки data\corpus не было — пропуск удаления.
)
poetry run dvc pull
if errorlevel 1 (
    echo ОШИБКА: dvc pull после удаления — корпус не восстановлен из MinIO.
    exit /b 1
)
if not exist data\corpus\en\sample_01.txt (
    echo ОШИБКА: после восстановления нет ожидаемых файлов корпуса.
    exit /b 1
)
echo Корпус восстановлен из MinIO (dvc pull^).
echo.

echo [6/7] Pytest (покрытие src 100%%)
poetry run pytest -q
if errorlevel 1 (
    echo ОШИБКА: тесты.
    exit /b 1
)
echo.

echo [7/7] lab_verify.py: .env, MinIO, корпус, детектор языка, DVC
poetry run python scripts/lab_verify.py
if errorlevel 1 (
    echo ОШИБКА: lab_verify.py
    exit /b 1
)
echo.
echo ============================================================
echo   Проверка завершена успешно.
echo ============================================================
echo.
exit /b 0
