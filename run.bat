@echo off
chcp 65001
echo.
pushd src
Title Geazer Selfbot Paid
mode con: cols=107 lines=45

%SYSTEMROOT%\py.exe --version > NUL 2>&1
IF %ERRORLEVEL% NEQ 0 GOTO attempt
%SYSTEMROOT%\py.exe -3.8 main.py
PAUSE
GOTO end

:attempt
py.exe --version > NUL 2>&1
IF %ERRORLEVEL% NEQ 0 GOTO lastattempt
py.exe -3.8 main.py
PAUSE
GOTO end

:lastattempt
python.exe --version > NUL 2>&1
IF %ERRORLEVEL% NEQ 0 GOTO message
python.exe main.py
PAUSE

:message
echo Couldn't find a valid Python ^>3.8 installation. Python needs to be installed and available in the PATH environment
cmd /k

:end