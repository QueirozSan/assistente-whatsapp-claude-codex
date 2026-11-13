' Inicia o mantenedor do responder SEM nenhuma janela (modo 0 = oculto de verdade, nem pisca).
Set sh = CreateObject("WScript.Shell")
pasta = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
sh.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & pasta & "\manter-responder.ps1""", 0, False
