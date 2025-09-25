Set WshShell = CreateObject("WScript.Shell")

' Install dependencies if needed (silently)
WshShell.Run "cmd /c python -c ""import pystray, PIL"" >nul 2>nul || pip install pystray pillow >nul 2>nul", 0, True

' Start the GUI completely invisibly
WshShell.Run "pythonw server_tray_gui.py", 0, False