@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
echo ========================================
echo ЛР: история коммитов, где менялся data\corpus.dvc
echo ========================================
git log --oneline -- data/corpus.dvc
exit /b %ERRORLEVEL%
