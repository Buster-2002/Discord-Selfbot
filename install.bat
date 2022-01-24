@echo off
chcp 65001
echo.
pushd src
Title Installing Requirements
mode con: cols=107 lines=40

%SYSTEMROOT%\py.exe --version > NUL 2>&1
IF %ERRORLEVEL% NEQ 0 GOTO attempt
%SYSTEMROOT%\py.exe -3.8 -m pip install -r ..\requirements.txt
GOTO end

:attempt
py.exe --version > NUL 2>&1
IF %ERRORLEVEL% NEQ 0 GOTO lastattempt
py.exe -3.8 -m pip install -r ..\requirements.txt
GOTO end

:lastattempt
python.exe --version > NUL 2>&1
IF %ERRORLEVEL% NEQ 0 GOTO message
python.exe -3.8 -m pip install -r ..\requirements.txt
GOTO end

:message
echo Couldn't find a valid Python ^>3.8 installation. Python needs to be installed and available in the PATH environment
cmd /k

:end
cls
Title Install Successful, Launching selfbot..
CALL run.bat
