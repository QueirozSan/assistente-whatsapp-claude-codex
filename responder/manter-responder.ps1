# Mantém o responder do WhatsApp (a assistente) sempre ligado; roda escondido, iniciado pela tarefa agendada.
# 04/11/2026: o Controle de Aplicativo do Windows bloqueia o pythonw.exe do .venv; usa o Python base do uv e o boot.py
# acrescenta as bibliotecas do .venv. Se o uv mudar de lugar, o boot cai para o .venv antigo.
$py  = Join-Path $env:APPDATA 'uv\python\cpython-3.11-windows-x86_64-none\pythonw.exe'
$app = Join-Path $PSScriptRoot 'boot.py'
if (-not (Test-Path $py)) { $py = Join-Path $PSScriptRoot '..\whatsapp-mcp-server\.venv\Scripts\pythonw.exe'; $app = Join-Path $PSScriptRoot 'responder.py' }
$log = Join-Path $PSScriptRoot 'responder.keeper.log'

$m = New-Object System.Threading.Mutex($false, 'Global\WhatsAppResponderKeeper')
if (-not $m.WaitOne(0)) { exit 0 }

while ($true) {
    Add-Content $log "$(Get-Date -Format s) iniciando responder"
    $p = Start-Process -FilePath $py -ArgumentList "-I `"$app`"" -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru
    $p.WaitForExit()
    Add-Content $log "$(Get-Date -Format s) responder saiu (codigo $($p.ExitCode)); religando em 15 s"
    Start-Sleep -Seconds 15
}
