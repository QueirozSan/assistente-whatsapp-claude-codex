# Assistente de WhatsApp com Claude Code ou Codex

Transforme o seu WhatsApp numa assistente pessoal com IA. Você manda mensagem (texto, áudio, foto, vídeo ou documento) e ela
**responde e executa tarefas no seu computador**: roda comandos, mexe em projetos, envia arquivos, guarda lembretes e
memória, entende piadas e responde até com figurinha. Quem usa o "cérebro" é o **Claude Code** ou o **Codex**, que você já tem.

*WhatsApp AI assistant powered by Claude Code or OpenAI Codex, built on whatsapp-mcp (Go bridge + Python MCP server). Windows-first, Portuguese UI.*

## O que vem pronto

| Peça | Pasta | O que faz |
|---|---|---|
| Ponte do WhatsApp | `whatsapp-bridge/` | Conecta no WhatsApp Web como "aparelho conectado" (QR code), guarda as mensagens num SQLite local e expõe uma API em `127.0.0.1:8080`. Envia texto, mídia e **figurinhas**. |
| Servidor MCP | `whatsapp-mcp-server/` | Deixa o Claude Code / Codex ler conversas, buscar contatos e mandar mensagens como ferramentas. |
| Assistente (responder) | `responder/` | Recebe as mensagens novas, decide se deve responder e chama o Claude Code ou o Codex. |

Recursos do responder:
- **Dono x outras pessoas.** Seu número (em `config.json`) tem acesso total. Outras pessoas só conversam, sem ferramentas, sem arquivos, numa pasta vazia, e só quando citam o nome da assistente.
- **Guarda de segurança** (`guarda.py`, com Claude Code): antes de apagar pastas, mexer em `.env`, chaves SSH, Git destrutivo ou fazer ordem/saque em corretora, ela **pede sua aprovação no WhatsApp**.
- **Áudio** transcrito localmente (faster-whisper), **fotos/vídeos/PDFs** analisados, álbum de fotos agrupado.
- **Progresso** de tarefas longas no WhatsApp, fila de tarefas, `cancelar`, limites contra spam e disjuntor.
- **Memória** entre conversas (`memoria.py`) e **lembretes** com aviso na hora (`lembretes.py`).
- **Personalidade** bem-humorada e **16 figurinhas** próprias (`responder/figurinhas/`): ela escreve `[[FIGURINHA: risada]]` e o responder envia.

## Instalação (Windows)

Pré-requisitos: [Go](https://go.dev/dl/) + compilador C (MSYS2 `ucrt64` gcc, para o SQLite), [uv](https://docs.astral.sh/uv/),
Python 3.11+ e **um** destes: [Claude Code](https://claude.com/claude-code) logado (`claude`) **ou** [Codex CLI](https://github.com/openai/codex) logado (`codex`).

1. `git clone` este repositório.
2. Rode **`INSTALAR-WHATSAPP.bat`**: compila a ponte, instala o servidor MCP, mostra o **QR code** (WhatsApp > Aparelhos conectados > Conectar aparelho) e deixa a ponte ligada 24 h.
3. Rode **`responder\INSTALAR-RESPONDER.bat`**: cria o `responder\config.json` a partir do exemplo e abre para você editar:
   - `numeros_acesso_total`: o **seu** número com DDI e DDD (ex.: `5511999999999`);
   - `pasta_de_trabalho`: a pasta onde ficam seus projetos;
   - `nome_assistente` e `gatilhos`: o nome dela (padrão **Luna**);
   - `motor`: `"claude"` (padrão) ou `"codex"`.
4. Mande no seu próprio WhatsApp: **"Luna, tudo bem?"**.

Mais fácil ainda: abra a pasta no **Claude Code** ou no **Codex** e diga *"instala esse projeto para mim"*. O `AGENTS.md` traz o passo a passo para o agente.

Voz (opcional): crie `responder\.venv-voz` com `faster-whisper` para transcrever áudios.

## Claude Code ou Codex?

| | Claude Code (`"motor": "claude"`) | Codex (`"motor": "codex"`) |
|---|---|---|
| Conversa contínua | sessão por conversa (expira em 12 h) | histórico em texto a cada pedido |
| Proteção | **guarda.py** pede aprovação no WhatsApp antes de ações perigosas | **sandbox** do Codex (`codex_sandbox`: `read-only`, `workspace-write` ou `danger-full-access`) |
| Escolha de modelo | automática (rápido no dia a dia, forte em tarefa difícil) | `modelo_codex` (vazio = padrão do Codex) |

## Privacidade e segurança

- Tudo roda **no seu computador**. As mensagens ficam em `whatsapp-bridge/store/` (fora do Git).
- `config.json`, `contexto.md`, memória, lembretes, logs e a sessão do WhatsApp estão no `.gitignore`. **Nunca** commite esses arquivos.
- A API da ponte só escuta em `127.0.0.1` e exige token (`store/.bridge-token`, criado sozinho).
- O WhatsApp não oferece API oficial para contas pessoais. Use com bom senso, sem disparo em massa, para não ter o número bloqueado.

## Créditos

Baseado em [lharries/whatsapp-mcp](https://github.com/lharries/whatsapp-mcp) e no fork
[verygoodplugins/whatsapp-mcp](https://github.com/verygoodplugins/whatsapp-mcp) (licença MIT). A ponte usa
[whatsmeow](https://github.com/tulir/whatsmeow). Assistente, figurinhas e instaladores em português: este repositório (MIT).
