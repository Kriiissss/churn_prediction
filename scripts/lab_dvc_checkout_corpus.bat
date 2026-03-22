@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
echo ========================================
echo ЛР: восстановить файлы корпуса по текущему data\corpus.dvc
echo (после git checkout на другой коммит)
echo ========================================
poetry run dvc checkout data/corpus.dvc
if errorlevel 1 (
    echo ОШИБКА: dvc checkout
    exit /b 1
)
echo Готово.
exit /b 0
