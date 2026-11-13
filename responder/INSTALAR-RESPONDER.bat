@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist config.json (
  copy config.example.json config.json >nul
  echo Criei responder\config.json. Troque os campos TROQUE ^(seu numero e a pasta dos projetos^) e salve.
  notepad config.json
)
if not exist contexto.md copy contexto.example.md contexto.md >nul
if not exist contexto_publico.md copy contexto_publico.example.md contexto_publico.md >nul
echo Registrando as tarefas do WhatsApp (Ponte e Responder) sem janela e com checagem a cada 5 min...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0registrar-tarefas.ps1"
echo.
echo Pronto. Teste: mande para voce mesmo no WhatsApp "Luna, tudo bem?" (ou o nome que voce pos em config.json).
pause
