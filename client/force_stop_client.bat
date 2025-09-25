@echo off
echo ================================
echo  Force Stop Clipboard Client
echo ================================
echo.

echo Stopping all client processes...

REM Kill Python client processes
echo Stopping Python client processes...
taskkill /f /im python.exe /fi "COMMANDLINE eq *client.py*" 2>nul
taskkill /f /im pythonw.exe /fi "COMMANDLINE eq *client.py*" 2>nul
taskkill /f /im python.exe /fi "COMMANDLINE eq *client_gui.py*" 2>nul
taskkill /f /im pythonw.exe /fi "COMMANDLINE eq *client_gui.py*" 2>nul

REM Alternative method - kill clipboard client processes
echo Checking for any remaining clipboard client processes...
wmic process where "CommandLine like '%%client.py%%' or CommandLine like '%%client_gui.py%%'" get ProcessId,CommandLine 2>nul | findstr /v /c:"No Instance"

echo.
echo ================================
echo  Client stop complete!
echo ================================
echo.
pause