# AGENTS.md — instruções para o Claude Code / Codex que for instalar ou mexer neste projeto

Responda ao usuário em português simples. Este repositório é a assistente de WhatsApp (ponte Go + servidor MCP Python +
responder). Leia o `README.md` primeiro.

## Instalar para o usuário (Windows)

1. Confira os pré-requisitos e instale o que faltar, pedindo permissão antes:
   - `go version`;
   - gcc do MSYS2 em `C:\msys64\ucrt64\bin` (CGO, necessário para o SQLite);
   - `uv --version`;
   - `claude --version` ou `codex --version`.
2. Rode `INSTALAR-WHATSAPP.bat`. O usuário precisa escanear o QR code no celular: avise e espere.
3. Crie `responder/config.json` a partir de `responder/config.example.json`. **Pergunte ao usuário** o número dele (DDI + DDD),
   a pasta de trabalho, o nome da assistente e o motor (`claude` ou `codex`). Nunca invente o número.
4. Copie `contexto.example.md` para `contexto.md` e `contexto_publico.example.md` para `contexto_publico.md`. Ajude o usuário a
   descrever os projetos dele em `contexto.md`.
5. Rode `responder\INSTALAR-RESPONDER.bat` (registra as tarefas agendadas `WhatsApp-Bridge` e `WhatsApp-Responder`).
6. Teste: `python responder\responder.py --teste "Luna, tudo bem?" --dono` (simula sem enviar). Depois peça ao usuário para
   mandar "Luna, tudo bem?" no WhatsApp dele e confira `responder/responder.log`.

## Regras

- **Nunca** commite nem imprima: `responder/config.json`, `contexto*.md` (exceto os `.example`), `memoria.json`, `lembretes.json`,
  `estado.json`, `sessoes.json`, `*.log`, `whatsapp-bridge/store/` (sessão do WhatsApp e mensagens), `.bridge-token`, `.env*`.
- A ponte só escuta em `127.0.0.1`. Não exponha a porta 8080 nem a 8769 na rede.
- Mudou o comportamento? Atualize o `README.md`.
- Testes: `cd whatsapp-bridge && go test ./...` (CGO ligado) e `cd whatsapp-mcp-server && uv run pytest`. No Windows, 6 testes
  de permissão de pasta já falham por natureza do sistema; não são regressão.

## Onde mexer

| Quer… | Arquivo |
|---|---|
| Personalidade, regras do dono, figurinhas | `responder/responder.py` (`montar_sistema`) e `responder/figurinhas/` |
| Ações que pedem aprovação | `responder/guarda_regras.json` (Claude Code) |
| Trocar Claude por Codex | `responder/config.json` → `"motor"` |
| Ferramentas MCP do WhatsApp | `whatsapp-mcp-server/main.py` |
| Envio de mídia/figurinha | `whatsapp-bridge/main.go` (`sendWhatsAppMessage`) |
