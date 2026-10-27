@echo off
chcp 65001 >nul
cd /d "%~dp0code"

where python >nul 2>nul
if errorlevel 1 goto try_py
python demo_asa_cases.py
goto done

:try_py
where py >nul 2>nul
if errorlevel 1 goto try_codex
py demo_asa_cases.py
goto done

:try_codex
set "CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%CODEX_PY%" goto no_python
"%CODEX_PY%" demo_asa_cases.py
goto done

:no_python
echo Python not found. Use PDF, screenshots, or video fallback.

:done
pause
