"""Busca diária de vagas: junta todas as fontes, aplica as regras do candidato, tira o que já foi visto
e gera a lista do dia ordenada por encaixe.

Fontes: empresas conhecidas (pesquisa/empresas.json, via Greenhouse/Lever/Ashby/Workable/
SmartRecruiters/Recruitee), Himalayas, Remotive e o portal público do Workable.
Exclusões: tudo que já está na planilha (planilha/candidaturas.csv, espelho da aba Candidaturas).

Uso: python pesquisa/busca_diaria.py [--max 40]
Saída: pesquisa/lista-do-dia.json
"""

import argparse
import csv
import html
import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

PASTA = Path(__file__).resolve().parent
RAIZ = PASTA.parent
sys.path.insert(0, str(PASTA))
import buscar_vagas as plataformas  # noqa: E402
from categorias import ORDEM, categorizar  # noqa: E402
from filtrar_vagas import SEM_CONTRATO, tipo_contrato  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (job-search script)", "Accept": "application/json"}

# --- Regras (INSTRUCOES.md) -------------------------------------------------------------
SENIOR_OU_ESTAGIO = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|manager|head|director|vp|vice president|chief|architect|expert|"
    r"intern(ship)?s?|trainee|apprentice|alternance|stagiaire|stage|graduate program)\b", re.I)
# Idioma acima do nível real (níveis reais do candidato) ou outro idioma exigido no título.
IDIOMA_ACIMA = re.compile(r"\bC1\b|\bC2\b|\bnative\b|\bnatif\b|fluent french|french[- ]speaking|"
                          r"\(fluent english & french\)", re.I)
OUTRO_IDIOMA = re.compile(r"\b(arabic|chinese|mandarin|cantonese|danish|swedish|norwegian|finnish|german|dutch|"
                          r"flemish|italian|spanish|polish|czech|slovak|hungarian|greek|turkish|russian|japanese|"
                          r"korean|hebrew|thai|vietnamese|romanian|bulgarian|croatian|serbian|ukrainian|hindi|"
                          r"tamil|telugu|bengali|malay|indonesian|tagalog|burmese)\b", re.I)
RELOCACAO = re.compile(r"work in [a-z]|relocat|work remote in (greece|bulgaria)|based in (?!france|europe)", re.I)
REMOTO = re.compile(r"remote|remoto|anywhere|worldwide|home based|distributed|global|t[ée]l[ée]travail", re.I)
REGIAO_OK = re.compile(r"anywhere|worldwide|global|europe|\beu\b|emea|france|paris|^\s*remote\s*$|remoto$", re.I)
REGIAO_RUIM = re.compile(r"united states|\busa?\b|us-based|canada|\bamer\b|\bnamer\b|americas|apac|latam|"
                         r"latin america|brazil|mexico|colombia|india|philippines|singapore|australia|japan|"
                         r"israel|north america|south africa|nigeria|kenya", re.I)
ENCAIXE = [
    (3, re.compile(r"customer (support|service|success|care|experience)|client (support|service)|support "
                   r"(agent|specialist|associate|representative|consultant)|help ?desk|portugu|brazil|bilingual|"
                   r"multilingual|service client|support client|conseiller", re.I)),
    (2, re.compile(r"\bjunior\b|\bjr\b|entry|associate|operations|moderat|virtual assistant|assistant|"
                   r"administrative|coordinator|onboarding|community|data (entry|annotation)|annotat|"
                   r"ai trainer|rater|evaluat|talent (community|pool)|general application|open application|"
                   r"spontan|java|backend", re.I)),
]


def nota(titulo: str) -> int:
    for pontos, padrao in ENCAIXE:
        if padrao.search(titulo):
            return pontos
    return 1


CIDADES_FRANCA = re.compile(r"\b(paris|lyon|marseille|bordeaux|nantes|lille|toulouse|nice|strasbourg|montpellier|"
                            r"rennes|grenoble|aix|annecy|ile-de-france|île-de-france|france)\b", re.I)
MANAGER_CLIENTE = re.compile(r"\b(account|customer success|community|client|clients|relationship|success|customer) manager\b", re.I)
IDF = re.compile(r"[iî]le[- ]de[- ]france|\bidf\b|paris|\b(75|77|78|91|92|93|94|95)\b|nanterre|boulogne|saint[- ]denis|"
                 r"cr[ée]teil|versailles|la d[ée]fense|issy|montreuil|levallois|neuilly|vincennes|massy|cergy|[ée]vry", re.I)
PARCIAL = re.compile(r"part[- ]time|temps partiel|mi-temps|\b(20|24|25|28|30)\s?h\b", re.I)


def HIBRIDA_IDF_PARCIAL(titulo, local):
    """Híbrida só vale se for meio período com presencial na Île-de-France."""
    return bool(re.search(r"hybrid|hybride", f"{titulo} {local}", re.I) and IDF.search(local or "") and PARCIAL.search(f"{titulo} {local}"))


EXPERIENTE = re.compile(r"\bexperienced\b|\b\d\+ years\b", re.I)


EMPRESAS_SEM_IA = re.compile(r"^canonical$", re.I)  # formulário proíbe IA (INSTRUCOES.md)
EMPRESAS_ENTREVISTA_IA = re.compile(r"^(micro1|mercor)$", re.I)  # exigem entrevista em vídeo com IA (o candidato não conseguiu)
DEV_JUNIOR = re.compile(r"\bjunior\b|\bjr\.?\b|entry|associate|graduate|d[ée]butant|\bintern\b", re.I)


LATAM = re.compile(r"brazil|brasil|latam|latin america|am[ée]rica latina", re.I)
EUROPA_OU_MUNDO = re.compile(r"europe|\beu\b|emea|france|portugal|worldwide|anywhere|global remote|^global$", re.I)
RESIDENCIA_LATAM = re.compile(r"must (be )?(based|located|reside|live) in (brazil|brasil|latam|latin america)|"
                              r"\bCLT\b|residente no brasil|based in brazil only|brazil only|latam only", re.I)
PORTUGUES = re.compile(r"portugu[eê]s|portuguese|portugais|brazilian|br[ée]silien", re.I)


def passa(titulo: str, local: str, empresa: str = "", contrato: str = "", regra: str = "nova") -> bool:
    local = local or ""
    if re.search(r"commission[- ]only", titulo + " " + (contrato or ""), re.I):
        return False  # sem pagamento fixo (freelance é aceito desde 2026-11-22)
    if regra == "nova" and RESIDENCIA_LATAM.search(titulo + " " + local):
        return False  # exige residência no Brasil/LATAM (ex.: CLT)
    if EMPRESAS_SEM_IA.search(empresa or "") or EMPRESAS_ENTREVISTA_IA.search(empresa or ""):
        return False
    # Nível de francês/inglês nunca é barreira (decisão de 2026-11-22); só idiomas que o candidato não fala.
    # "Manager" em função de cliente não é chefia (decisão de 2026-11-22); "Senior ... Manager" continua barrado.
    if SENIOR_OU_ESTAGIO.search(MANAGER_CLIENTE.sub(" ", titulo)) or OUTRO_IDIOMA.search(titulo):
        return False
    if RELOCACAO.search(titulo):  # tempo de experiência nunca barra (decisão de 2026-11-22)
        return False
    if HIBRIDA_IDF_PARCIAL(titulo, local):
        return True  # híbrida em meio período na Île-de-France: aceita (decisão de 2026-11-22)
    if not REMOTO.search(local + " " + titulo):
        return False
    # (Revertido em 2026-11-22: liberar qualquer região só trouxe vagas "Remoto - EUA"; o candidato decidiu que elas
    # gastam token e baixam a assertividade. Vale: sem região, França, Europa, EMEA ou mundo todo.)
    # A marca "remoto" (acrescentada pela leitura da plataforma) diz só que é remoto; a região é o resto.
    regiao = re.sub(r"\s*\b(remoto|remote|hybrid|onsite)\s*$", "", local, flags=re.I).strip()
    if not regiao or re.fullmatch(r"(remote|remote job)", regiao, re.I):
        return True
    if re.search(r"\bhq\b|\bna\b|u\.s\.", regiao, re.I):
        return False
    if CIDADES_FRANCA.search(regiao):
        return True
    if regra == "nova":
        # Cita Brasil/LATAM e também Europa/EMEA/França/Portugal/mundo: aceita.
        if LATAM.search(regiao) and EUROPA_OU_MUNDO.search(regiao):
            return True
    if REGIAO_RUIM.search(regiao):
        return False
    return bool(re.search(r"anywhere|worldwide|global remote|remote[,\s-]+global|^global$|europe|\beu\b|emea|^remote\b|\bremote$", regiao, re.I))


def pede_portugues(texto: str) -> bool:
    return bool(PORTUGUES.search(texto or ""))


# --- Fontes ---------------------------------------------------------------------------
def obter(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def fonte_empresas():
    empresas = json.loads((PASTA / "empresas.json").read_text(encoding="utf-8"))

    def uma(item):
        nome, info = item
        if isinstance(info, dict) and info.get("ativa") is False:
            return []  # empresa que nunca rendeu vaga útil (regra "lago certo", 2026-11-23)
        funcao = plataformas.PLATAFORMAS.get(info["plataforma"])
        if not funcao:
            return []
        try:
            return [dict(v, empresa=nome, fonte=info["plataforma"], tipo_empresa=info.get("tipo")) for v in funcao(info["slug"])]
        except Exception:
            return []

    with ThreadPoolExecutor(12) as ex:
        return [v for lista in ex.map(uma, empresas.items()) for v in lista]


def fonte_himalayas():
    vagas = []
    for q in ["customer support", "customer service", "support specialist", "portuguese", "bilingual",
              "virtual assistant", "data annotation", "ai trainer", "operations", "junior", "moderator",
              # ampliação de 2026-11-22: funções variadas remotas na Europa
              "game tester", "gaming", "player support", "community", "content moderator", "trust and safety",
              "event coordinator", "entertainment", "travel", "booking", "translator", "localization",
              "transcription", "data entry", "chat support", "social media", "tutor", "french", "entry level"]:
        for extra in ("&country=FR", "&worldwide=true"):
            try:
                dados = obter("https://himalayas.app/jobs/api/search?q=" + q.replace(" ", "%20") + extra)
            except Exception:
                continue
            for v in dados.get("jobs", []):
                loc = ", ".join(v.get("locationRestrictions") or []) or "Worldwide"
                if len(loc) > 120:  # listas enormes de países = Europa ampla
                    loc = "Europe" if "France" in loc else loc[:120]
                vagas.append({"empresa": v.get("companyName", ""), "titulo": v.get("title", ""), "local": loc,
                              "link": v.get("applicationLink") or v.get("guid", ""), "fonte": "himalayas"})
    return vagas


def fonte_remotive():
    vagas = []
    for cat in ["customer-support", "all-others", "admin", "qa", "sales-business", "writing", "hr"]:
        try:
            dados = obter(f"https://remotive.com/api/remote-jobs?category={cat}&limit=150")
        except Exception:
            continue
        for v in dados["jobs"]:
            vagas.append({"empresa": v["company_name"], "titulo": v["title"], "local": v.get("candidate_required_location", ""),
                          "link": v["url"], "fonte": "remotive"})
    return vagas


def fonte_workable():
    vagas = []
    for q in ["customer support", "customer service", "support client", "portuguese", "virtual assistant", "junior"]:
        for loc in ("&location=France", ""):
            try:
                dados = obter("https://jobs.workable.com/api/v1/jobs?query=" + q.replace(" ", "%20") + loc + "&workplace=remote")
            except Exception:
                continue
            for v in dados.get("jobs", []):
                l = v.get("location") or {}
                local = f"{l.get('city') or ''} {l.get('countryName') or ''} remoto".strip()
                vagas.append({"empresa": (v.get("company") or {}).get("title", ""), "titulo": v.get("title", ""),
                              "local": local, "link": v.get("url", ""), "fonte": "workable-portal"})
    return vagas


def fonte_francetravail():
    import francetravail
    return francetravail.buscar(paginas=3)


def fonte_jobicy():
    """Jobicy (API pública, robots permite /api): vagas remotas já filtradas por região."""
    vagas, vistos = [], set()
    for geo in ("france", "europe", "emea", "anywhere", "portugal"):
        try:
            dados = obter(f"https://jobicy.com/api/v2/remote-jobs?count=100&geo={geo}")
        except Exception:
            continue
        for v in dados.get("jobs", []):
            if v.get("id") in vistos:
                continue
            vistos.add(v.get("id"))
            local = (v.get("jobGeo") or "").replace("  ", " ")
            vagas.append({"empresa": v.get("companyName", ""), "titulo": html.unescape(v.get("jobTitle", "")),
                          "local": f"{local} remoto", "link": v.get("url", ""), "fonte": "jobicy",
                          "nivel": v.get("jobLevel", "")})
    return vagas


def fonte_apis():
    """APIs oficiais (chaves no cofre). Se uma falhar (chave recusada, fora do ar), a outra segue."""
    import apis_emprego
    saida = []
    for nome, func in (("Adzuna", apis_emprego.adzuna), ("France Travail API", apis_emprego.francetravail)):
        try:
            saida += func()
        except Exception as e:  # noqa: BLE001
            print(f"  aviso: {nome} falhou ({str(e)[:80]})")
    return saida


FONTES_MANUAIS = {  # bloqueiam acesso automatizado (403) ou o robots.txt proíbe: o candidato abre à mão
    "Welcome to the Jungle (403)": "https://www.welcometothejungle.com/fr/jobs?query={q}&refinementList%5Bremote%5D%5B%5D=fulltime",
    "Indeed.fr (403)": "https://fr.indeed.com/jobs?q={q}&l=t%C3%A9l%C3%A9travail",
    "HelloWork (robots.txt proíbe)": "https://www.hellowork.com/fr-fr/emploi/recherche.html?k={q}&t=Complet",
}


# --- Exclusões ------------------------------------------------------------------------
def ja_vistas():
    arquivo = RAIZ / "planilha" / "candidaturas.csv"
    empresas_vaga, links = set(), set()
    if arquivo.exists():
        for linha in csv.DictReader(arquivo.open(encoding="utf-8")):
            empresas_vaga.add((linha.get("empresa", "").lower(), (linha.get("vaga") or "").lower()))
            for campo in ("link_vaga", "endereco_ou_link"):
                if linha.get(campo):
                    links.add(linha[campo].split("?")[0].rstrip("/"))
    return empresas_vaga, links


def empresas_recentes(dias=90):
    """Empresas com candidatura enviada nos últimos `dias` (regra: 1 candidatura por empresa a cada 90 dias)."""
    from datetime import datetime, timedelta
    arquivo = RAIZ / "planilha" / "candidaturas.csv"
    limite, recentes = datetime.now() - timedelta(days=dias), set()
    if arquivo.exists():
        for linha in csv.DictReader(arquivo.open(encoding="utf-8")):
            try:
                if datetime.strptime(linha.get("data_envio", ""), "%d/%m/%Y") >= limite:
                    recentes.add(linha["empresa"].lower().strip())
            except ValueError:
                continue
    return recentes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=40)
    args = parser.parse_args()

    todas = []
    for fonte in (fonte_empresas, fonte_himalayas, fonte_remotive, fonte_workable, fonte_francetravail, fonte_apis, fonte_jobicy):
        try:
            achadas = fonte()
        except Exception as e:  # uma fonte fora do ar não derruba a busca
            print(f"{fonte.__name__}: falhou ({e})")
            continue
        print(f"{fonte.__name__}: {len(achadas)} vagas")
        todas += achadas

    (PASTA / "vagas-brutas-dia.json").write_text(json.dumps(todas, ensure_ascii=False), encoding="utf-8")
    vistas_par, vistos_links = ja_vistas()
    recentes = empresas_recentes()
    resultado, chaves = [], set()
    for v in todas:
        chave = (v["empresa"].lower().strip(), v["titulo"].lower().strip())
        link = (v.get("link") or "").split("?")[0].rstrip("/")
        if chave in chaves or chave in vistas_par or link in vistos_links or chave[0] in recentes:
            continue
        chaves.add(chave)
        if passa(v["titulo"], v.get("local", ""), v["empresa"], v.get("contrato", "")):
            v["contrato"] = tipo_contrato(v["titulo"] + " " + v.get("contrato", ""))
            v["encaixe"] = 4 if pede_portugues(v["titulo"]) else nota(v["titulo"])  # português: prioridade máxima
            v["categoria"] = categorizar(v["titulo"], "", v.get("tipo_empresa"))
            if v["categoria"] == "dev" and not DEV_JUNIOR.search(v["titulo"]):
                continue  # dev só júnior/entrada (foco terciário)
            resultado.append(v)
    resultado.sort(key=lambda v: (ORDEM.index(v["categoria"]), -v["encaixe"], v["empresa"].lower()))

    saida = {"data": date.today().isoformat(), "total_lidas": len(todas), "candidatas": resultado}
    (PASTA / "lista-do-dia.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(f"\n{len(todas)} vagas lidas, {len(resultado)} candidatas novas.")
    print("Por categoria:", dict(Counter(v["categoria"] for v in resultado)))
    print("Por fonte:    ", dict(Counter(v["fonte"] for v in resultado)))
    print("\nFontes manuais (bloqueiam acesso automatizado; abrir no navegador):")
    from urllib.parse import quote_plus
    for nome, modelo in FONTES_MANUAIS.items():
        for termo in ("conseiller client télétravail", "support client portugais", "customer support portuguese", "player support"):
            print(f"   {nome:32} {termo:32} {modelo.format(q=quote_plus(termo))}")
    print(f"\nMelhores {args.max}:")
    for v in resultado[: args.max]:
        print(f"[{v['categoria']:15}|{v['encaixe']}] {v['empresa'][:22]} | {v['titulo'][:60]} | {v['contrato'][:18]} | {v.get('local', '')[:25]} | {v['fonte']} | {v['link']}")


if __name__ == "__main__":
    main()
