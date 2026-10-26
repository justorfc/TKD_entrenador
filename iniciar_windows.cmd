@echo off
setlocal
cd /d "%~dp0"
py app.py
if errorlevel 1 (
  echo.
  echo No se pudo iniciar. Compruebe Python y Tcl/Tk con: py -m tkinter
  pause
)
endlocal
