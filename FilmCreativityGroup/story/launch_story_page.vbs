Set WshShell = CreateObject("WScript.Shell")
base = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
cmdPath = base & "\\launch_story_page.cmd"

WshShell.Run "cmd /c """ & cmdPath & """", 0, False
WScript.Sleep 9000
WshShell.Run "explorer.exe http://127.0.0.1:5173/", 1, False
