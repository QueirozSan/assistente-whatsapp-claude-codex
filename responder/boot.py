"""Inicia o responder com o Python do uv + as bibliotecas do .venv do whatsapp-mcp-server.

Por quê (04/11/2026): o Controle de Aplicativo do Windows passou a bloquear os executáveis python.exe/pythonw.exe do
.venv (WinError 4551) — o responder em execução seguia vivo, mas não voltaria num reinício, e os alertas/relatório que ele
chama por subprocesso já falhavam desde a manhã. O interpretador base do uv é liberado; o .venv só fornece as bibliotecas.
Uso (manter-responder.ps1): <uv>\\pythonw.exe -I boot.py [argumentos do responder]
"""
import os
import runpy
import site
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
site.addsitedir(os.path.normpath(os.path.join(AQUI, "..", "whatsapp-mcp-server", ".venv", "Lib", "site-packages")))
sys.path.insert(0, AQUI)
sys.argv = [os.path.join(AQUI, "responder.py"), *sys.argv[1:]]
runpy.run_path(sys.argv[0], run_name="__main__")
