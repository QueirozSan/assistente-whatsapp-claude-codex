"""Lembretes do dono: lista numerada guardada em lembretes.json. Usada pelo relatório, pelo responder e pelo Luna.

Itens do dono (dia ou semana) e recomendações do agente (💡, vindas dos alertas urgentes do relatório). Uma recomendação
excluída pelo dono não volta por 7 dias; quando o problema some, ela sai da lista sozinha.
Uso (CLI, é o que o Luna roda):  python lembretes.py lista
                                    python lembretes.py add "Comprar leite e banana" [--semana] [--quando "amanhã 9h"]
                                    python lembretes.py del 2 [4 ...]
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta

AQUI = os.path.dirname(os.path.abspath(__file__))
ARQ = os.path.join(AQUI, "lembretes.json")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def ler():
    try:
        with open(ARQ, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d.setdefault("itens", [])
    d.setdefault("dispensados", {})
    return d


def gravar(d):
    tmp = ARQ + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ARQ)


def capitalizar(t):
    t = " ".join(str(t).split()).strip(" .;")
    return t[:1].upper() + t[1:]


def adicionar(texto, prazo="dia", origem="dono", chave=None, quando=None):
    d = ler()
    texto = capitalizar(texto)
    if any(i["texto"].lower() == texto.lower() and i.get("quando") == quando for i in d["itens"]):
        return None
    d["itens"].append({"texto": texto, "prazo": prazo, "origem": origem, "chave": chave, "criado": time.time(), "quando": quando})
    gravar(d)
    return texto


def vencidos():
    """Lembretes com horário que chegaram na hora e ainda não foram avisados. Marca como avisados. [(número, texto)]"""
    d = ler()
    out = []
    for n, i in enumerate(d["itens"], 1):
        if i.get("quando") and not i.get("avisado") and i["quando"] <= time.time():
            i["avisado"] = time.time()
            out.append((n, i["texto"]))
    if out:
        gravar(d)
    return out


# ---------------------------------------------------------------- horário ("amanhã às 9h", "em 30 min", "dia 10", "sexta à tarde")
SEMANA = {"segunda": 0, "terca": 1, "terça": 1, "quarta": 2, "quinta": 3, "sexta": 4, "sabado": 5, "sábado": 5, "domingo": 6}
DIA_SEM = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")
RE_EM = re.compile(r"(?i)\b(?:daqui a|daqui|em|dentro de)\s+(\d{1,3}|uma?|meia)\s*(min(?:uto)?s?|h(?:ora)?s?)\b(?:\s+e\s+meia)?")
RE_HORA = re.compile(r"(?i)\b(?:[àa]s?|para as|pras|às)?\s*(\d{1,2})(?:(?::|h)(\d{2})|\s*h(?:oras?)?\b|(?=\s+(?:da|de)\s+(?:manh[ãa]|tarde|noite)))(?:\s+(?:da|de)\s+(manh[ãa]|tarde|noite))?")
RE_PERIODO = re.compile(r"(?i)\b(?:de|à|a|na|pela)\s+(manh[ãa]|tarde|noite)\b|\bao meio[- ]dia\b")
RE_DIA = re.compile(r"(?i)\b(hoje|amanh[ãa]|depois de amanh[ãa])\b|\bdia\s+(\d{1,2})(?:/(\d{1,2}))?\b|\b(?:na|no|nesta|neste|esta|este|pr[óo]xim[ao])?\s*"
                    r"(segunda|ter[çc]a|quarta|quinta|sexta|s[áa]bado|domingo)(?:-feira)?\b")


def ler_quando(t, agora=None):
    """(timestamp, texto sem a expressão de tempo) ou (None, t) se não houver horário/dia."""
    agora = agora or datetime.now()
    m = RE_EM.search(t)
    if m:
        n = {"um": 1, "uma": 1, "meia": 0.5}.get(m.group(1).lower(), None) or float(m.group(1))
        seg = n * (60 if m.group(2).lower().startswith("m") else 3600) + (1800 if "e meia" in m.group(0).lower() else 0)
        return (agora + timedelta(seconds=seg)).timestamp(), limpar(t[:m.start()] + " " + t[m.end():])
    dia, hora, resto = None, None, t
    md = RE_DIA.search(resto)
    if md:
        hoje = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        if md.group(1):
            dia = hoje + timedelta(days={"hoje": 0}.get(md.group(1).lower(), 2 if "depois" in md.group(1).lower() else 1))
        elif md.group(2):
            mes = int(md.group(3)) if md.group(3) else agora.month
            try:
                dia = hoje.replace(month=mes, day=int(md.group(2)))
                if dia < hoje:
                    dia = dia.replace(year=dia.year + 1) if md.group(3) else (dia.replace(month=mes % 12 + 1, year=dia.year + (mes == 12)))
            except ValueError:
                dia = None
        else:
            alvo = SEMANA[md.group(4).lower().replace("ç", "c") if md.group(4).lower().replace("ç", "c") in SEMANA else md.group(4).lower()]
            dia = hoje + timedelta(days=(alvo - hoje.weekday()) % 7 or 7)
        if dia:
            resto = resto[:md.start()] + " " + resto[md.end():]
    mh = RE_HORA.search(resto)
    if mh and int(mh.group(1)) <= 23 and (mh.group(2) is None or int(mh.group(2)) < 60):
        h, mi = int(mh.group(1)), int(mh.group(2) or 0)
        if (mh.group(3) or "").lower() in ("tarde", "noite") and h < 12:
            h += 12
        hora = (h, mi)
        resto = resto[:mh.start()] + " " + resto[mh.end():]
    else:
        mp = RE_PERIODO.search(resto)
        if mp:
            hora = (12, 0) if "meio" in mp.group(0).lower() else {"manha": (9, 0), "manhã": (9, 0), "tarde": (14, 0), "noite": (20, 0)}[mp.group(1).lower()]
            resto = resto[:mp.start()] + " " + resto[mp.end():]
    if not dia and not hora:
        return None, t
    h, mi = hora or (9, 0)
    base = dia or agora.replace(hour=0, minute=0, second=0, microsecond=0)
    alvo = base.replace(hour=h, minute=mi)
    if not dia and alvo <= agora:
        alvo += timedelta(days=1)
    return alvo.timestamp(), limpar(resto)


def limpar(t):
    t = " ".join(t.split()).strip(" .,:;-")
    return re.sub(r"(?i)^(?:de|que|pra|para|pro|a)\s+(?:eu\s+)?", "", t).strip(" .,:;-")


def quando_txt(ts, agora=None):
    agora = agora or datetime.now()
    d = datetime.fromtimestamp(ts)
    hm = d.strftime("%H:%M")
    dif = (d.date() - agora.date()).days
    if dif == 0:
        return f"hoje às {hm}"
    if dif == 1:
        return f"amanhã às {hm}"
    return f"{DIA_SEM[d.weekday()]} {d.strftime('%d/%m')} às {hm}"


def remover(numeros):
    """Remove pela posição exibida (1 = primeiro). Devolve os textos removidos."""
    d = ler()
    fora = []
    for n in sorted(set(numeros), reverse=True):
        if 1 <= n <= len(d["itens"]):
            item = d["itens"].pop(n - 1)
            fora.append((n, item["texto"]))
            if item.get("chave"):
                d["dispensados"][item["chave"]] = time.time()
    gravar(d)
    return sorted(fora)


def sincronizar_recomendacoes(recs):
    """recs: [(chave, texto)] dos alertas urgentes de hoje. Acrescenta as novas e tira as resolvidas."""
    d = ler()
    agora = time.time()
    d["dispensados"] = {k: t for k, t in d["dispensados"].items() if agora - t < 7 * 86400}
    ativas = {k for k, _ in recs}
    d["itens"] = [i for i in d["itens"] if i.get("origem") != "agente" or i.get("chave") in ativas]
    textos = dict(recs)
    for i in d["itens"]:
        if i.get("origem") == "agente" and i.get("chave") in textos:
            i["texto"] = capitalizar(textos[i["chave"]])  # o alerta mudou de texto: atualiza sem mudar a posição
    tem = {i.get("chave") for i in d["itens"]}
    for k, t in recs:
        if k not in tem and k not in d["dispensados"]:
            d["itens"].append({"texto": capitalizar(t), "prazo": "dia", "origem": "agente", "chave": k, "criado": agora})
    gravar(d)


def linhas():
    d = ler()
    out = []
    for i, it in enumerate(d["itens"], 1):
        marca = "💡 " if it.get("origem") == "agente" else ""
        quando = " _(semana)_" if it.get("prazo") == "semana" else ""
        if it.get("quando"):
            quando = " _(⏰ avisado)_" if it.get("avisado") else f" _(⏰ {quando_txt(it['quando'])})_"
        out.append(f"{i}. {marca}{it['texto']}{quando}")
    return out


def texto_lista(titulo="📝 *LEMBRETES*"):
    ls = linhas()
    corpo = "\n".join(ls) if ls else "Nenhum lembrete. Para adicionar: _coloca na lista comprar leite_"
    return f"{titulo}\n{corpo}"


# ---------------------------------------------------------------- entender a mensagem do dono (sem IA)
RE_ADD = re.compile(r"^(?:adiciona|adicione|coloca|coloque|p[oõ]e|ponha|bota|anota|anote|inclui|inclua|acrescenta|acrescente|salva|salve)\b"
                    r"(?:\s+(?:a[ií]|isso|tamb[eé]m))?"
                    r"(?:\s+(?:na|no|nos|nas|em|[aà])\s+(?:minha\s+|meus\s+)?(?:lista|lembretes?)(?:\s+(?:do dia|de hoje|da semana))?)?"
                    r"(?:\s*[:,-]?\s*(?:pra|para|de|que|a)\s+(?:eu\s+)?|\s*[:,-]\s*|\s+)"
                    r"(?P<t>.+)$", re.IGNORECASE | re.DOTALL)
RE_DEL_VERBO = re.compile(r"^(?:exclu[ií]r?|exclua|apaga[r]?|apague|remove[r]?|remova|tira[r]?|tire|deleta[r]?|delete|conclu[ií]r?|conclua|"
                          r"marca[r]?|finaliza[r]?)\b", re.IGNORECASE)
RE_FEITO = re.compile(r"\b(feito|feitos|feita|feitas|conclu[ií]d[oa]s?|pronto|prontos|finalizad[oa]s?|ok|check|resolvid[oa]s?|j[aá] fiz)\b", re.IGNORECASE)
RE_LEMBRA = re.compile(r"^(?:me\s+)?(?:lembr(?:a|e|ar)|avis(?:a|e|ar))(?:-me)?(?:\s+(?:me|de mim))?\s+(?P<t>.+)$", re.IGNORECASE | re.DOTALL)
RE_LISTA = re.compile(r"^(?:ver |mostra(?:r)? (?:os |a |meus |minha )?)?(?:lembretes?|lista|minha lista|lista de lembretes|meus lembretes)[\s?!.]*$", re.IGNORECASE)


def interpretar(texto):
    """("lista",) | ("del", [números]) | ("add", texto, prazo) | None."""
    t = " ".join(texto.split()).strip()
    if RE_LISTA.match(t):
        return ("lista",)
    nums = [int(x) for x in re.findall(r"\b\d{1,3}\b", t)]
    fala_de_lembrete = re.search(r"(?i)\blembretes?\b|\bitens?\b|\btarefas?\b|\bda lista\b", t)
    so_numeros = re.fullmatch(r"(?i)[\w\s,eé.!]*", t) and len(t) <= 60
    if nums and so_numeros and not RE_LEMBRA.match(t) and (RE_DEL_VERBO.match(t) or RE_FEITO.search(t)) and (fala_de_lembrete or RE_FEITO.search(t) or RE_DEL_VERBO.match(t)):
        sem_numero = re.sub(r"\d+|\b(e|o|os|a|as|lembretes?|itens?|tarefas?|da lista|n[uú]mero|de|do)\b|[,.!]", " ", t, flags=re.IGNORECASE)
        if len(sem_numero.split()) <= 3:  # "excluir lembrete 2", "lembrete 5 feito", "feito 2 e 4"
            return ("del", nums)
    ml = RE_LEMBRA.match(t)
    if ml and not t.endswith("?"):  # "me lembra amanhã às 9h de ligar pro João"; sem horário entra na lista do dia
        ts, item = ler_quando(ml.group("t"))
        item = limpar(item)
        pediu = re.match(r"(?i)^(me\s|lembre-me|avise-me)", t) or ts  # "lembra daquele site" sem "me" nem horário é conversa
        if item and pediu:
            return ("add", item, "dia", ts)
    m = RE_ADD.match(t)
    if m and re.search(r"(?i)\b(lista|lembretes?)\b", t):
        item = m.group("t")
        item = re.sub(r"(?i)^(?:(?:na|no|nos|nas|em|[aà])\s+(?:minha\s+)?(?:lista|lembretes?)(?:\s+(?:do dia|de hoje|da semana))?\s*)", "", item)
        item = re.sub(r"(?i)^(?:pra|para|de|que)\s+(?:eu\s+)?", "", item)
        prazo = "semana" if re.search(r"(?i)\b(semana|essa semana|esta semana|até sexta)\b", t) else "dia"
        item = re.sub(r"(?i)\s*\b(?:na|no|nos|nas|[aà])\s+(?:minha\s+)?(?:lista|lembretes?)(?:\s+(?:do dia|de hoje|da semana))?\b", "", item)
        item = re.sub(r"(?i)\s*\b(?:essa|esta|da)\s+semana\b", "", item).strip(" .,:")
        ts, item = ler_quando(item)
        if item:
            return ("add", item, prazo, ts)
    return None


def executar(acao):
    """Aplica a ação e devolve a resposta para o WhatsApp."""
    if acao[0] == "lista":
        return texto_lista()
    if acao[0] == "del":
        fora = remover(acao[1])
        if not fora:
            return "Não achei esse número na lista.\n\n" + texto_lista()
        feitos = "\n".join(f"✅ {n}. {t}" for n, t in fora)
        return f"Excluído da lista:\n{feitos}\n\n" + texto_lista("📝 *Lista atualizada*")
    quando = acao[3] if len(acao) > 3 else None
    novo = adicionar(acao[1], acao[2], quando=quando)
    if not novo:
        return "Esse lembrete já está na lista.\n\n" + texto_lista()
    if quando:
        return f"⏰ Combinado: te aviso {quando_txt(quando)}: {novo}\n\n" + texto_lista()
    return f"📌 Adicionado{' (semana)' if acao[2] == 'semana' else ''}: {novo}\n\n" + texto_lista()


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "lista":
        print(texto_lista())
    elif a[0] == "add" and len(a) > 1:
        ts = ler_quando(a[a.index("--quando") + 1])[0] if "--quando" in a and a.index("--quando") + 1 < len(a) else None
        print(executar(("add", a[1], "semana" if "--semana" in a else "dia", ts)))
    elif a[0] == "del" and len(a) > 1:
        print(executar(("del", [int(x) for x in a[1:] if x.isdigit()])))
    else:
        print(__doc__)
