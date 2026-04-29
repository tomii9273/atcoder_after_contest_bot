@echo off
setlocal

schtasks /Create /SC HOURLY /MO 4 /TN "AtCoderAfterContestBot" /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File ""%~dp0run_bot.ps1""" /ST 08:00 /F

endlocal
