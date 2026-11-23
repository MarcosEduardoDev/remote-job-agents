"""Fila de vagas: o estado de cada vaga na operação, compartilhado por todos os agentes.

Arquivo: fila/fila.json (uma entrada por vaga, chave = id curto do link).
Status, na ordem do fluxo:
  triada            passou na triagem por script (pronta para o redator)
  ler_no_navegador  o script não conseguiu ler a vaga (Himalayas, France Travail, Adzuna...): vai para o leitor
  barrada           caiu numa barreira (anos, híbrida, região...) - fim
  pacote            o redator montou o pacote em candidaturas/pendentes/ - vai para o verificador
  aprovada          o verificador deu APROVADO - vai para o candidatador
  reprovada         o verificador deu REPROVADO - volta ao redator (corrigir) ou vira pulada
  enviada           enviada e confirmada - fim
  falta_voce        formulário preenchido, falta o candidato (captcha, teste, decisão) - ver relatório do dia
  pulada            não vale a pena / regra de negócio impede - fim

Uso (linha de comando, para os agentes):
  python pesquisa/fila.py resumo
  python pesquisa/fila.py listar <status> [limite]
  python pesquisa/fila.py mostrar <id>
  python pesquisa/fila.py mudar <id> <status> "<nota>" [--pacote caminho]
"""

import contextlib
import hashlib
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO = RAIZ / "fila" / "fila.json"
STATUS = ["triada", "ler_no_navegador", "barrada", "fora_lista", "manual", "pacote", "aprovada", "reprovada", "enviada", "falta_voce",
          "pulada"]
FINAIS = {"barrada", "enviada", "pulada"}


# Decisão de 2026-11-22: a fila automática (redator -> verificador -> candidatador) só recebe vagas cuja
# candidatura é feita em Greenhouse, Lever, Ashby ou Workable. O resto vai para a "Fila manual" do candidato.
import re as _re

PLATAFORMAS_AUTO = {
    "greenhouse": _re.compile(r"greenhouse\.io|gh_jid=", _re.I),
    "lever": _re.compile(r"jobs\.lever\.co", _re.I),
    "ashby": _re.compile(r"ashbyhq\.com", _re.I),
    "workable": _re.compile(r"apply\.workable\.com|jobs\.workable\.com/view", _re.I),
    # Ampliação de 2026-11-23 (decisão do candidato): formulários simples.
    "recruitee": _re.compile(r"\.recruitee\.com", _re.I),
    "teamtailor": _re.compile(r"\.teamtailor\.com|career\.[a-z0-9-]+\.[a-z]+/jobs/\d+", _re.I),
    "smartrecruiters": _re.compile(r"smartrecruiters\.com", _re.I),
}
# Agregadores só redirecionam: o leitor precisa achar o site final antes de decidir.
AGREGADORES = _re.compile(r"himalayas\.app|adzuna\.|remotive\.com|candidat\.francetravail\.fr|jooble|indeed\.|jobicy\.com", _re.I)
# Plataformas excluídas por regra (entrevista em vídeo com IA): nunca entram, nem pela fila manual.
BLOQUEADAS = _re.compile(r"micro1\.ai|mercor\.com|work\.mercor", _re.I)
# Destinos que proíbem automação, pedem vídeo ou conta não autorizada: vão para a Fila manual.
MANUAIS = _re.compile(r"hellowork\.com|welcometothejungle\.com|talentview\.io|apec\.fr|successfactors|myworkdayjobs\.com|"
                      r"indeed\.|linkedin\.com", _re.I)


LOCAL_FORA = _re.compile(
    r"\b(us|usa|u\.s\.|united states|canada|mexico|brazil|brasil|argentina|chile|colombia|peru|latam|latin america|"
    r"americas|north america|apac|asia|india|philippines|singapore|japan|tokyo|korea|china|australia|new zealand|"
    r"south africa|nigeria|kenya|egypt|turkey|t[üu]rkiye|israel|uae|dubai|saudi|"
    r"new york|san francisco|seattle|austin|boston|chicago|toronto|vancouver|montreal|sydney|melbourne|manila|"
    r"bangalore|bengaluru|mumbai|s[ãa]o paulo|buenos aires|bogot[áa]|mexico city|atlanta|denver|miami|"
    r"remote[- ]us|us[- ]remote|remote \(us|remote \(canada)\b", _re.I)
LOCAL_OK = _re.compile(r"france|paris|europe|\beu\b|european union|emea|worldwide|anywhere|global|schengen|"
                       r"\bremote\b(?!\s*[-(]\s*(us|usa|canada|americas|apac))", _re.I)


def _norm_empresa(nome):
    nome = _re.sub(r"\(.*?\)|\s+-\s*$|\b(sas|sasu|sarl|sa|inc|ltd|gmbh|group|groupe)\b", " ", (nome or "").lower())
    return " ".join(_re.sub(r"[^a-z0-9à-ü ]", " ", nome).split())


def _mesma_empresa(a, b):
    """'Eduneo Distanciel' e 'Eduneo' são a mesma empresa (primeira palavra igual, com 5+ letras)."""
    if not a or not b:
        return False
    return a == b or (a.split()[0] == b.split()[0] and len(a.split()[0]) >= 5)


def ja_enviada(empresa, dias=90):
    """Data do último envio para a empresa nos últimos `dias` (planilha/candidaturas.csv), ou None."""
    import csv
    from datetime import timedelta
    alvo = _norm_empresa(empresa)
    if not alvo:
        return None
    limite = datetime.now() - timedelta(days=dias)
    try:
        with open(RAIZ / "planilha" / "candidaturas.csv", encoding="utf-8") as f:
            for linha in csv.DictReader(f):
                if _mesma_empresa(_norm_empresa(linha.get("empresa")), alvo) and linha.get("data_envio"):
                    if datetime.strptime(linha["data_envio"], "%d/%m/%Y") >= limite:
                        return linha["data_envio"]
    except FileNotFoundError:
        pass
    return None


def plataforma(url):
    url = url or ""
    for nome, padrao in PLATAFORMAS_AUTO.items():
        if padrao.search(url):
            return nome
    if BLOQUEADAS.search(url):
        return "bloqueada"
    if AGREGADORES.search(url):
        return "agregador"
    return "manual"


def rota(e):
    """Para onde vai uma vaga que passou na triagem: (status, nota)."""
    from categorias import categorizar, na_lista_branca
    # A área vem só do título (2026-11-23): pela descrição, quase tudo virava "atendimento".
    cat = categorizar(e.get("titulo") or "", "", None)
    e["categoria"] = cat
    if not na_lista_branca(cat, e.get("titulo")):
        return "fora_lista", f"fora da lista branca ({cat}): vai para o relatório de revisão"
    e["categoria"] = cat
    # Regra de 2026-11-23: o agente não lê vaga cujo local já diz outro país/região (decidido por script).
    local = (e.get("local") or "").lower()
    if LOCAL_FORA.search(local) and not LOCAL_OK.search(local):
        return "barrada", f"local fora da França/Europa ({e.get('local')}): descartada por script"
    # Regra de 2026-11-23: empresa que já recebeu candidatura nos últimos 90 dias não chega a nenhum agente
    # (a France Travail republica a mesma oferta com outro número).
    data = ja_enviada(e.get("empresa"))
    if data:
        return "pulada", f"empresa já recebeu candidatura em {data} (regra dos 90 dias): descartada por script"
    destino = e.get("destino") or e.get("link") or ""
    p = plataforma(destino)
    if p in PLATAFORMAS_AUTO:
        return "triada", f"fila automática ({p})"
    if p == "bloqueada":
        return "pulada", "destino excluído por regra (micro1/Mercor: entrevista com IA)"
    if p == "agregador":
        return "ler_no_navegador", "agregador: o leitor precisa achar o site final"
    origem_agregador = bool(AGREGADORES.search(e.get("link") or ""))
    prioridade = "Baixa" if "adzuna." in (e.get("link") or "") else "Normal"
    e["prioridade_manual"] = prioridade
    e["motivo_manual"] = ("site proíbe automação, pede vídeo ou conta" if MANUAIS.search(destino)
                          else "plataforma fora da fila automática")
    return "manual", f"fila manual ({e['motivo_manual']}; prioridade {prioridade}" + (", veio de agregador)" if origem_agregador else ")")


def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def ident(link):
    base = (link or "").split("?")[0].rstrip("/").lower()
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:10]


@contextlib.contextmanager
def trava(espera=60):
    """Só um processo por vez lê-modifica-grava a fila (vários agentes rodam em paralelo)."""
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    lock = ARQUIVO.parent / ".trava"
    inicio = time.time()
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.time() - inicio > espera:
                os.remove(lock)  # trava esquecida por um processo que caiu
                continue
            time.sleep(0.2)
    try:
        yield
    finally:
        os.close(fd)
        os.remove(lock)


def carregar():
    if ARQUIVO.exists():
        return json.loads(ARQUIVO.read_text(encoding="utf-8"))
    return {}


def salvar(fila):
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    tmp = ARQUIVO.with_suffix(".tmp")
    tmp.write_text(json.dumps(fila, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(ARQUIVO)


def mudar(fila, i, status, nota="", pacote=None, origem="agente"):
    if status not in STATUS:
        raise SystemExit(f"status inválido: {status} (use um de {STATUS})")
    e = fila[i]
    e["status"] = status
    e["origem"] = origem  # "script" (rodada) ou "agente" (decisão de um agente: a rodada não desfaz)
    e["atualizado"] = agora()
    if pacote:
        e["pacote"] = pacote
    e.setdefault("historico", []).append({"quando": agora(), "status": status, "nota": nota})


def incluir(fila, v, status, nota=""):
    """Inclui uma vaga nova ou atualiza dados de uma que ainda não saiu da triagem. Não mexe nas que já andaram."""
    i = ident(v.get("link"))
    campos = {k: v.get(k) for k in ("empresa", "titulo", "link", "destino", "fonte", "local", "categoria", "contrato",
                                     "encaixe", "barreiras", "avisos", "erro")}
    if i not in fila:
        fila[i] = {"id": i, **campos, "criado": agora()}
        mudar(fila, i, status, nota, origem="script")
        return True
    # Só reavalia o que a própria rodada decidiu (a regra pode ter mudado); decisão de agente não é desfeita.
    if fila[i]["status"] in ("triada", "ler_no_navegador", "barrada") and fila[i].get("origem", "script") == "script":
        fila[i].update(campos)
        if fila[i]["status"] != status:
            mudar(fila, i, status, nota, origem="script")
    return False


def resumo(fila):
    return Counter(e["status"] for e in fila.values())


def main():
    args = sys.argv[1:]
    fila = carregar()
    if not args or args[0] == "resumo":
        r = resumo(fila)
        print(f"{len(fila)} vagas na fila: " + ", ".join(f"{s} {r[s]}" for s in STATUS if r[s]))
    elif args[0] == "listar":
        st = args[1]
        lim = int(args[2]) if len(args) > 2 else 999
        itens = sorted((e for e in fila.values() if e["status"] == st), key=lambda e: (-(e.get("encaixe") or 0), e["empresa"] or ""))
        for e in itens[:lim]:
            av = " [aviso idioma]" if e.get("avisos") else ""
            print(f"{e['id']} | {e.get('categoria', ''):15} | {(e['empresa'] or '')[:22]} | {(e['titulo'] or '')[:55]} | "
                  f"{(e.get('contrato') or '')[:15]}{av} | {e.get('destino') or e['link']}")
    elif args[0] == "mostrar":
        print(json.dumps(fila[args[1]], ensure_ascii=False, indent=1))
    elif args[0] == "mudar":
        pacote = args[args.index("--pacote") + 1] if "--pacote" in args else None
        with trava():
            fila = carregar()
            mudar(fila, args[1], args[2], args[3] if len(args) > 3 and not args[3].startswith("--") else "", pacote)
            salvar(fila)
        print(f"{args[1]} -> {args[2]}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
