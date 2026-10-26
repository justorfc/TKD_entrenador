@echo off
setlocal
cd /d "%~dp0"
echo Preparando el entorno de construccion de TKD Entrenador...
py -m venv .venv_build
if errorlevel 1 goto error
".venv_build\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto error
".venv_build\Scripts\python.exe" -m pip install pyinstaller
if errorlevel 1 goto error
".venv_build\Scripts\python.exe" -m unittest -v test_core.py
if errorlevel 1 goto error
".venv_build\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name TKD_Entrenador app.py
if errorlevel 1 goto error
".venv_build\Scripts\python.exe" -m pip freeze > versiones_compilacion.txt
echo.
echo Ejecutable creado: dist\TKD_Entrenador.exe
echo Pruebelo primero con datos ficticios en un equipo Windows sin Python.
pause
exit /b 0
:error
echo.
echo No se completo la construccion. Revise el mensaje anterior.
pause
exit /b 1
