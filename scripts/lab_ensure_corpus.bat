@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
if exist "data\corpus\en\sample_01.txt" (
    echo [ЛР] Корпус уже есть: data\corpus\en\sample_01.txt
    exit /b 0
)
echo [ЛР] Корпус не найден — запуск генерации...
call "%~dp0lab_generate_corpus.bat"
exit /b %ERRORLEVEL%
