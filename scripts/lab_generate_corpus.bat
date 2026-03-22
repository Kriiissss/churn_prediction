@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
echo ========================================
echo ЛР: генерация корпуса data\corpus (en, fr, de, es)
echo ========================================
poetry run python scripts/generate_corpus_data.py
exit /b %ERRORLEVEL%
