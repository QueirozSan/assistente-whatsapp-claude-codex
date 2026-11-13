# Recria as tarefas WhatsApp-Responder e WhatsApp-Bridge para rodarem SEM janela (via wscript + .vbs)
# e com checagem a cada 5 min (se o mantenedor cair, volta sozinho; cópia duplicada é barrada pelo mutex).
$resp = $PSScriptRoot
$raiz = Split-Path $resp

function Registrar($nome, $vbs, $descricao) {
    Stop-ScheduledTask -TaskName $nome -ErrorAction SilentlyContinue
    $acao = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument "`"$vbs`""
    $gatilhos = @(
        (New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME),
        (New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5))
    )
    $cfg = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
        -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $nome -Action $acao -Trigger $gatilhos -Settings $cfg -Description $descricao -Force | Out-Null
}

# Encerra os mantenedores antigos (os que abrem janela) e o responder em execução
Get-CimInstance Win32_Process |
    Where-Object { $_.Name -match '^(powershell|pwsh)\.exe$' -and $_.CommandLine -match 'manter-(responder|bridge)\.ps1' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Get-CimInstance Win32_Process |
    Where-Object { $_.Name -match '^pythonw?\.exe$' -and $_.CommandLine -match 'responder\\responder\.py' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Registrar 'WhatsApp-Responder' (Join-Path $resp 'iniciar-oculto.vbs') 'Responde no WhatsApp quando o dono escreve a assistente (sem janela)'
Registrar 'WhatsApp-Bridge' (Join-Path $raiz 'iniciar-ponte-oculto.vbs') 'Ponte do WhatsApp 24h (sem janela)'
Start-ScheduledTask -TaskName 'WhatsApp-Bridge'
Start-Sleep -Seconds 8
Start-ScheduledTask -TaskName 'WhatsApp-Responder'
Write-Host 'Pronto: tarefas recriadas sem janela.'
