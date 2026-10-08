@echo off
rem Fixture: references a helper script that does not exist.
python "%~dp0tools\build.py" %*
