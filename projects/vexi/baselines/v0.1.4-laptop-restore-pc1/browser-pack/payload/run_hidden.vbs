Set sh = CreateObject("WScript.Shell")
root = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
cmd = Chr(34) & root & "\.venv\Scripts\pythonw.exe" & Chr(34) & " " & Chr(34) & root & "\pack_service.py" & Chr(34) & " --browser vivaldi --port 8767 --credential-target " & Chr(34) & "browser_pack/vivaldi" & Chr(34)
sh.Run cmd, 0, False
