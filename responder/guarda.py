"""Guarda de ações perigosas: o Claude Code executa este script ANTES de cada ferramenta (hook PreToolUse).

- Ação comum (quase tudo, inclusive publicar, git push, servidor, mensagens): sai sem dizer nada (liberada). Decisão do dono
  em 2026-11-02: só pede autorização para o que é realmente importante.
- Ação importante (apagar projeto/pasta, perder trabalho no Git, apagar banco, dinheiro real): BLOQUEIA e pergunta ao dono NA
  CONVERSA em que ele deu a ordem, privado ou grupo. Ele libera com "sim" (ou "pode", "confirmo"...) RESPONDENDO (citando) a
  mensagem do pedido, ou escrevendo "sim CÓDIGO". Um "sim" solto nunca vale: evita aprovar sem querer numa conversa sobre
  outro assunto (decisão do dono em 2026-11-03). A resposta só vale se vier DO DONO, depois do pedido, no banco da ponte (não dá para forjar pelo webhook), uma
  vez só, por 15 min, e só para o pedido mais recente. "não" cancela.
- Bloqueio total (sem aprovação possível): mexer em arquivos do próprio guarda/aprovações, token e banco da ponte.
- Falha do guarda = bloqueia (fail-closed).
Limite honesto: protege contra acidente e contra instrução maliciosa vinda de texto; um agente com shell e má-fé
deliberada pode tentar contornar. As regras ficam em guarda_regras.json.
"""
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
STORE = os.path.join(RAIZ, "whatsapp-bridge", "store")
PEND = os.path.join(AQUI, "pendentes.json")
VALIDADE_PEDIDO_S = 3600  # um pedido pendente some depois de 1 h
VALIDADE_APROVACAO_S = 900  # o "sim" vale por 15 min
MARCA = "​"
# Respostas que contam como aprovação (mensagem inteira). Mantido em sincronia com o responder.py.
APROVA = re.compile(r"^(sim|s|pode|pode (sim|ir|fazer|executar|apagar|seguir|continuar)|confirmo|confirmar|confirmado|"
                    r"autorizo|autorizado|aprovo|aprovado|aprovar|libera|liberado|manda ver|faz|fa[cç]a|vai sim)"
                    r"(\s+(?P<cod>[A-Za-z0-9]{4}))?[\s,!.]*(por favor|pf)?[\s!.]*$", re.IGNORECASE)


def saida_negar(motivo):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": motivo}}, ensure_ascii=True))
    sys.exit(0)


def regras():
    with open(os.path.join(AQUI, "guarda_regras.json"), encoding="utf-8") as f:
        return json.load(f)


def texto_da_acao(nome, ent):
    if nome in ("Bash", "PowerShell"):
        return " ".join(str(ent.get("command", "")).split())
    if nome in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        return str(ent.get("file_path") or ent.get("notebook_path") or "")
    return json.dumps(ent, ensure_ascii=False, sort_keys=True)


def alvo_livre(alvo, seguro, sensivel, cwd):
    """Pasta descartável (cache, build...) ou um arquivo comum: não precisa de autorização."""
    if seguro.search(alvo):
        return True
    if any(c in alvo for c in "*?$%") or sensivel.search(alvo):
        return False
    caminho = os.path.expanduser(re.sub(r"^/([a-zA-Z])/", r"\1:/", alvo))
    if not os.path.isabs(caminho):
        caminho = os.path.join(cwd or ".", caminho)
    return not os.path.isdir(caminho)  # arquivo solto (ou que nem existe) é livre; PASTA pede autorização


def exclusao_segura(cmd, r, cwd=""):
    """True se TODO comando de apagar do texto mira só coisas descartáveis ou arquivos soltos, nunca pastas ou projetos."""
    seguro = re.compile(r["pastas_seguras_para_apagar"], re.IGNORECASE)
    sensivel = re.compile(r["arquivos_sensiveis_apagar"], re.IGNORECASE)
    achou = False
    for seg in re.split(r"[;&|]+", cmd):
        m = re.match(r"\s*(?:sudo\s+)?(rm|remove-item|ri|del|erase|rmdir|rd)\b(.*)", seg, re.IGNORECASE)
        if not m:
            continue
        alvos = []
        for tok in re.findall(r"\"[^\"]+\"|'[^']+'|\S+", m.group(2)):
            tok = tok.strip("\"'")
            if tok.startswith("-") or re.fullmatch(r"/[a-zA-Z]", tok) or tok.lower() in ("-recurse", "-force"):
                continue
            alvos.append(tok)
        if not alvos or any(a in ("*", ".", "..", "~") or not alvo_livre(a, seguro, sensivel, cwd) for a in alvos):
            return False
        achou = True
    return achou


def classificar(nome, ent, r, cwd=""):
    """Devolve a categoria de perigo ou None."""
    if nome in ("Bash", "PowerShell"):
        cmd = texto_da_acao(nome, ent)
        for regra in r["bash"]:
            pad, cat, flag = regra[0], regra[1], (regra[2] if len(regra) > 2 else "")
            if re.search(pad, cmd, re.IGNORECASE):
                if flag == "apagar" and exclusao_segura(cmd, r, cwd):
                    continue
                return cat
        for pads, cat in r["bash_combinados"]:
            if all(re.search(p, cmd, re.IGNORECASE) for p in pads):
                return cat
    elif nome in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        caminho = texto_da_acao(nome, ent)
        for pad, cat in r["caminhos_escrita"]:
            if re.search(pad, caminho, re.IGNORECASE):
                return cat
    elif nome.startswith("mcp__"):
        for regra in r["mcp"]:
            pad, cat, flag = regra[0], regra[1], (regra[2] if len(regra) > 2 else "")
            if re.search(pad, nome, re.IGNORECASE):
                if flag == "sql" and not re.search(r"\b(delete\s+from|drop|truncate)\b",
                                                   str(ent.get("query", "")), re.IGNORECASE):
                    continue  # consulta de leitura
                return cat
    return None


def ler_pendentes():
    try:
        with open(PEND, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def gravar_pendentes(d):
    tmp = PEND + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(tmp, PEND)


def aprovacao_no_banco(criado, usadas, chat="", codigo=""):
    """Id de uma mensagem do DONO aprovando ("sim"...), na conversa do pedido ou no privado dele, recebida DEPOIS do pedido,
    ainda válida e não usada; ou None."""
    dono = os.environ.get("ASSISTENTE_DONO", "")
    if not dono:
        return None
    caminho = os.environ.get("ASSISTENTE_DB") or os.path.join(STORE, "messages.db")
    c = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True, timeout=5)
    try:
        linhas = c.execute("SELECT id, timestamp, content, quoted_message_id, chat_jid FROM messages WHERE is_from_me=0 AND sender=? "
                           "AND chat_jid IN (?, ?) ORDER BY timestamp DESC LIMIT 12", (dono, chat, f"{dono}@s.whatsapp.net")).fetchall()
        citadas = {}
        for _, _, _, qid, cj in linhas:
            if qid:
                r = c.execute("SELECT content FROM messages WHERE id=? AND chat_jid=?", (qid, cj)).fetchone()
                citadas[qid] = (r[0] if r else "") or ""
    finally:
        c.close()
    for mid, ts, content, qid, _ in linhas:
        m = APROVA.match(re.sub(r"^\s*\w+\s*[,:]\s*", "", content or "").strip())
        if mid in usadas or not m:
            continue
        if not codigo or not ((m.group("cod") or "").upper() == codigo or f"Código: {codigo}" in citadas.get(qid, "")):
            continue  # "sim" solto não vale: tem de citar o pedido ou trazer o código
        try:
            t = datetime.fromisoformat(str(ts).replace(" ", "T", 1))
            if t.tzinfo is None:
                t = t.astimezone()
            t = t.timestamp()
        except ValueError:
            continue
        if t >= criado - 2 and time.time() - t <= VALIDADE_APROVACAO_S:
            return mid
    return None


def avisar_dono(categoria, resumo, codigo):
    if os.environ.get("ASSISTENTE_SEM_ALERTA"):
        return
    dono = os.environ.get("ASSISTENTE_DONO", "")
    if not dono:
        return
    with open(os.path.join(STORE, ".bridge-token"), encoding="utf-8") as f:
        token = f.read().strip()
    texto = (f"🔐 *Preciso da sua aprovação:* {categoria}\n{resumo}\n\nCódigo: {codigo}\n"
             f"Para liberar, *responda a esta mensagem* com *sim*, ou escreva *sim {codigo}*. Para cancelar, *não {codigo}*.\n"
             "Um \"sim\" solto não vale. Vale 15 min, uma vez só." + MARCA)
    req = urllib.request.Request("http://127.0.0.1:8080/api/send",
                                 data=json.dumps({"recipient": os.environ.get("ASSISTENTE_CHAT") or f"{dono}@s.whatsapp.net", "message": texto}).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    urllib.request.urlopen(req, timeout=15).read()


def resumo_curto(nome, ent):
    txt = texto_da_acao(nome, ent)
    txt = re.sub(r"(?i)\b(key|token|secret|senha|password|passwd|apikey|api_key)\b\s*[=:]\s*\S+", r"\1=***", txt)
    txt = re.sub(r"\b[A-Za-z0-9_\-]{32,}\b", "***", txt)
    if nome.startswith("mcp__"):
        txt = nome.replace("mcp__", "") + " " + txt
    return (txt[:240] + "…") if len(txt) > 240 else txt


def main():
    ev = json.load(sys.stdin)
    nome = ev.get("tool_name", "")
    ent = ev.get("tool_input") or {}
    r = regras()
    bruto = json.dumps(ent, ensure_ascii=False)
    for pad in r["bloqueio_total"]:
        if re.search(pad, bruto, re.IGNORECASE):
            saida_negar("BLOQUEADO PERMANENTEMENTE: esta ação mexe em arquivos de segurança do WhatsApp/guarda. "
                        "Não há aprovação possível. Não tente contornar; explique ao dono que isso é proibido.")
    categoria = classificar(nome, ent, r, ev.get("cwd", ""))
    if not categoria:
        sys.exit(0)  # ação comum (inclui toda leitura): liberada

    h = hashlib.sha256((nome + "|" + texto_da_acao(nome, ent)).encode()).hexdigest()[:16]
    agora = time.time()
    todos = ler_pendentes()
    usadas = set(todos.get("__usadas", []))
    pend = {c: p for c, p in todos.items() if c != "__usadas" and agora - p["criado"] < VALIDADE_PEDIDO_S}
    achado = next(((c, p) for c, p in pend.items() if p["hash"] == h), None)
    if achado:
        codigo, p = achado
        mid = aprovacao_no_banco(p["criado"], usadas, p.get("chat", ""), codigo)  # o código liga o "sim" a ESTE pedido
        if mid:
            del pend[codigo]  # uso único
            pend["__usadas"] = (list(usadas) + [mid])[-50:]
            gravar_pendentes(pend)
            sys.exit(0)  # APROVADO pelo dono: libera esta execução
        saida_negar("AINDA SEM APROVAÇÃO. O dono já foi avisado nesta conversa. Pare esta tarefa agora e responda em uma frase "
                    "curta que aguarda a aprovação. Não repita o aviso nem tente outra forma de fazer a mesma coisa.")
    codigo = "".join(c for c in hashlib.sha256(f"{h}{agora}".encode()).hexdigest().upper() if c not in "O0I1L")[:4]
    pend[codigo] = {"hash": h, "criado": agora, "categoria": categoria, "acao": texto_da_acao(nome, ent)[:1500],
                    "resumo": resumo_curto(nome, ent), "chat": os.environ.get("ASSISTENTE_CHAT", "")}
    pend["__usadas"] = list(usadas)[-50:]
    gravar_pendentes(pend)
    try:
        avisar_dono(categoria, resumo_curto(nome, ent), codigo)
    except Exception:  # noqa: BLE001 - mesmo sem conseguir avisar, continua bloqueado
        pass
    saida_negar(f"BLOQUEADO: ação perigosa ({categoria}) precisa da aprovação do dono. Já perguntei ao dono nesta conversa. "
                "Pare esta tarefa agora e responda em UMA frase curta dizendo que aguarda a aprovação (não repita a "
                "descrição, o dono já recebeu). Quando ele aprovar, você será chamado de novo para repetir EXATAMENTE a "
                "mesma ação.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"guarda falhou ({e}); bloqueado por segurança", file=sys.stderr)
        sys.exit(2)
