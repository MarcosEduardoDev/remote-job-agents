"""Triagem detalhada da lista do dia: descobre o link real de candidatura de cada vaga (inclusive as
do Himalayas), lê a descrição e marca requisitos que barram o candidato.

Uso: python pesquisa/triagem_detalhada.py <n primeiras candidatas> [--pular empresa1,empresa2]
Saída: pesquisa/triagem-detalhada.json e uma tabela no terminal.
"""

import html
import json
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from categorias import categorizar  # noqa: E402
from filtrar_vagas import tipo_contrato  # noqa: E402

PASTA = Path(__file__).resolve().parent
UA = {"User-Agent": "Mozilla/5.0"}
ATS = re.compile(r"https?://[^\s\"'<>]*(?:greenhouse\.io|lever\.co|ashbyhq\.com|workable\.com|recruitee\.com|"
                 r"smartrecruiters\.com|teamtailor\.com|bamboohr\.com|breezy\.hr|jobs\.personio|factorialhr|"
                 r"welcometothejungle|typeform\.com|forms\.gle|docs\.google\.com/forms)[^\s\"'<>]*", re.I)
BARREIRAS = {
    "anos": re.compile(r"\b([3-9]|1\d)\+?\s*(?:years|yrs|ans)\b", re.I),
    "c1_ou_nativo": re.compile(r"\b(C1|C2|native[- ]level|native (english|french|speaker)s?|(english|french) native|natif|"
                               r"mother tongue|langue maternelle|fran[cç]ais (courant|natif)|parfaite ma[iî]trise du fran[cç]ais|"
                               r"ma[iî]tris(ez|er) parfaitement le fran[cç]ais|native[- ]level (fluency in )?(english|french))\b", re.I),
    "frances_fluente": re.compile(r"(fluent|fluency|courant|excellent)[^.\n]{0,40}french|french[^.\n]{0,20}(fluent|native|C1)", re.I),
    "diploma": re.compile(r"(?<!no )(?<!not )bachelor'?s degree (is )?required|(?<!no )(?<!not )degree (is )?required|"
                          r"dipl[oô]me (bac\+|requis)", re.I),
    "eua_canada": re.compile(r"must (be )?(reside|live|located|based) in (the )?(us|usa|united states|canada|uk|united kingdom|"
                             r"australia|india|philippines|brazil|mexico|latin america|latam|germany|spain|portugal|greece)|"
                             r"(only|exclusively) (open to|for) (candidates|applicants|residents) (in|of|from)|"
                             r"(right|authori[sz]ed|eligible) to work in the (us|united states|uk|united kingdom)|"
                             r"us citizens? only|"
                             r"authorized to work in the (us|united states)", re.I),
    "entrevista_ia": re.compile(r"ai (pre-?)?interview|ai[- ]led interview|ai screening|interview with (our )?ai|"
                                r"video interview with ai", re.I),
    "presencial": re.compile(r"location:\s*on-?site|this (is an|role is) on-?site|on-?site (role|position)|"
                             r"must (work|be) (from|in) (our|the) office|poste en pr[ée]sentiel", re.I),
    "hibrida": re.compile(r"\bhybrid\b|\b[1-4] days? (a|per) week (in|at|from) (the |our )?office|in[- ]office (days|presence)|"
                          r"[1-4] jours? (par semaine )?(sur site|au bureau|en pr[ée]sentiel)|t[ée]l[ée]travail partiel", re.I),
    "fatura": re.compile(r"must (be able to )?invoice|registered business|siret|auto-?entrepreneur", re.I),
}


def _hibrida_aceita(v, corpo):
    """Híbrida em meio período com presencial na Île-de-France é aceita (decisão de 2026-11-22)."""
    from busca_diaria import IDF, PARCIAL
    return bool(IDF.search(f"{v.get('local', '')} {corpo[:600]}") and PARCIAL.search(f"{v.get('titulo', '')} {corpo}"))


def baixar(url, tentativas=4):
    """Lê a página com novas tentativas: a conexão do candidato tem quedas curtas de DNS."""
    import time
    for n in range(tentativas):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError:
            raise
        except Exception:
            if n == tentativas - 1:
                raise
            time.sleep(5 * (n + 1))


# Decisão de 2026-11-22: exigência de idioma acima do real (fluente, nativo, C1, parfait) não barra mais a vaga;
# vira aviso no pacote (o formulário que perguntar o nível recebe a resposta real).
SO_AVISO = {"c1_ou_nativo", "frances_fluente", "anos"}  # experiência nunca barra (decisão de 2026-11-22)

_CACHE_ASHBY = {}


def descricao_api(link):
    """Descrição completa pelas APIs públicas das plataformas (as páginas são montadas por JavaScript)."""
    m = re.match(r"https://jobs\.ashbyhq\.com/([^/]+)/([0-9a-f-]{36})", link)
    if m:
        org, ident = m.groups()
        if org not in _CACHE_ASHBY:
            _CACHE_ASHBY[org] = json.loads(baixar(f"https://api.ashbyhq.com/posting-api/job-board/{org}"))["jobs"]
        for j in _CACHE_ASHBY[org]:
            if j.get("id") == ident:
                return f"{j.get('workplaceType', '')} {j.get('employmentType', '')} {j.get('location', '')} " + (j.get("descriptionPlain") or "")
        return "VAGA FECHADA (não está mais no quadro da Ashby)"
    m = re.match(r"https://(?:job-boards|boards)\.(?:eu\.)?greenhouse\.io/([^/]+)/jobs/(\d+)", link)
    if m:
        d = json.loads(baixar(f"https://boards-api.greenhouse.io/v1/boards/{m.group(1)}/jobs/{m.group(2)}"))
        return texto(html.unescape(d.get("content", ""))) + " " + d.get("location", {}).get("name", "")
    m = re.match(r"https://jobs\.lever\.co/([^/]+)/([0-9a-f-]{36})", link)
    if m:
        d = json.loads(baixar(f"https://api.lever.co/v0/postings/{m.group(1)}/{m.group(2)}"))
        return f"{d.get('workplaceType', '')} {d.get('categories', {}).get('commitment', '')} " + d.get("descriptionPlain", "") + " " + " ".join(
            texto(x.get("content", "")) for x in d.get("lists", [])) + " " + d.get("additionalPlain", "")
    m = re.match(r"https://jobs\.workable\.com/view/([^/]+)", link)
    if m:
        d = json.loads(baixar(f"https://jobs.workable.com/api/v1/jobs/{m.group(1)}"))
        return texto(" ".join(d.get(k) or "" for k in ("description", "requirementsSection", "benefitsSection"))) + " " + str(d.get("employmentType"))
    return None


def texto(bruto):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", bruto, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))


def analisar(v):
    link, destino, barreiras, avisos, erro, corpo = v["link"], v["link"], [], [], "", ""
    try:
        via_api = descricao_api(link)
        bruto = via_api if via_api is not None else baixar(link)
        if via_api is None and ("himalayas.app" in link or "jobicy.com" in link):
            achados = [u for u in ATS.findall(html.unescape(bruto)) if "himalayas" not in u]
            if achados:
                destino = achados[0].split("?")[0].rstrip("\\")
        corpo = bruto if via_api is not None else texto(bruto)
        if corpo.startswith("VAGA FECHADA"):
            barreiras.append("vaga fechada")
        for nome, padrao in BARREIRAS.items():
            m = padrao.search(corpo)
            if m:
                trecho = f"{nome}: '{corpo[max(0, m.start() - 40):m.end() + 40].strip()}'"
                excecao = nome == "hibrida" and _hibrida_aceita(v, corpo)
                (avisos if nome in SO_AVISO or excecao else barreiras).append(trecho)
    except Exception as e:  # página bloqueada ou fora do ar
        erro = str(e)[:80]
    categoria = categorizar(v.get("titulo", ""), "", v.get("tipo_empresa"))
    if categoria == "outro":  # o título não decidiu: tenta com a descrição
        categoria = categorizar(v.get("titulo", ""), corpo, v.get("tipo_empresa"))
    contrato = tipo_contrato(" ".join([v.get("titulo", ""), v.get("contrato", ""), corpo]))
    # Freelance aceito desde 2026-11-22: o tipo de contrato fica só como informação no pacote.
    return dict(v, destino=destino, barreiras=barreiras, avisos=avisos, erro=erro, categoria=categoria, contrato=contrato)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    pular = set()
    if "--pular" in sys.argv:
        pular = {p.strip().lower() for p in sys.argv[sys.argv.index("--pular") + 1].split(",")}
    lista = json.loads((PASTA / "lista-do-dia.json").read_text(encoding="utf-8"))["candidatas"]
    lista = [v for v in lista if v["empresa"].lower() not in pular][:n]
    with ThreadPoolExecutor(3) as ex:
        resultado = list(ex.map(analisar, lista))
    (PASTA / "triagem-detalhada.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    for i, v in enumerate(resultado, 1):
        estado = "OK" if not v["barreiras"] and not v["erro"] else ("ERRO" if v["erro"] else "BARRA")
        print(f"{i:2} {estado:5} | {v['categoria']:15} | {v['contrato'][:18]:18} | {v['empresa'][:22]} | {v['titulo'][:45]} | {v['destino'][:80]}")
        for b in v["barreiras"][:2]:
            print(f"        - {b[:150]}")


if __name__ == "__main__":
    main()
