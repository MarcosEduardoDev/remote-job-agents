"""Aplica a regra principal do candidato às vagas de pesquisa/vagas-brutas*.json.

Qualquer função serve. Descarta só: não remota, restrita a outro país/região, sênior/chefia,
estágio que exige faculdade. Pré-filtro por título e local; a descrição ainda precisa ser lida.
Saída: pesquisa/vagas-candidatas.json
"""

import json
import re
from pathlib import Path

PASTA = Path(__file__).resolve().parent

SENIOR_OU_ESTAGIO = [
    r"\bsenior\b", r"\bsr\.?\b", r"\bstaff\b", r"\bprincipal\b", r"\blead\b", r"\bmanager\b", r"\bhead\b",
    r"\bdirector\b", r"\bvp\b", r"vice president", r"\bchief\b", r"\bceo\b", r"\bcto\b", r"\bsvp\b",
    r"\bintern(ship)?s?\b", r"\btrainee\b", r"\bstagiaire\b", r"\balternance\b", r"\bapprentice",
    r"\bexperienced\b", r"\bexpert\b", r"\barchitect\b", r"\bgeneral manager\b", r"\bcounsel\b", r"\bofficer\b",
]
OUTRO_IDIOMA = r"\b(arabic|chinese|mandarin|danish|swedish|norwegian|finnish|german|dutch|italian|spanish|polish|czech|slovak|hungarian|greek|turkish|russian|japanese|korean|hebrew|thai|vietnamese|romanian|bulgarian|croatian|serbian|ukrainian|hindi|indonesian|malay)\b"
# Local precisa ser remoto E sem restrição a outra região.
REMOTO = [r"remote", r"remoto", r"anywhere", r"worldwide", r"home based", r"distributed", r"\bglobal\b"]
REGIAO_RUIM = [
    r"united states", r"\bUSA?\b", r"us-based", r"canada", r"\bAMER\b", r"\bNAMER\b", r"\bNA\b", r"americas",
    r"\bAPAC\b", r"\bLATAM\b", r"latin america", r"brazil", r"mexico", r"india", r"hyderabad", r"singapore",
    r"australia", r"japan", r"china", r"israel", r"north america", r"south america", r"central america",
]
REGIAO_OK = [r"anywhere", r"worldwide", r"europe", r"\bEMEA\b", r"france", r"global"]


# Só contrato de trabalho (salarié). Decisão do candidato em 2026-11-21: nada de freelance/auto-entrepreneur.
SEM_CONTRATO = re.compile(
    r"\bfreelance[r]?\b|\bfree-lance\b|\bcontractor\b|independent contractor|\b1099\b|\bb2b contract|"
    r"\bcontrat b2b\b|auto-?entrepreneur|micro-?entrepreneur|portage salarial|self-?employed|commission[- ]only|"
    r"\bind[ée]pendant\.?e?\b|prestataire ind[ée]pendant|statut d.ind[ée]pendant|\bagent commercial\b|"
    r"\bon a contract basis\b|contract position \(freelance\)", re.I)
# Tipo de contrato quando aparece (para gravar no pacote).
TIPOS_CONTRATO = [
    ("EOR (employee)", re.compile(r"employer of record|\bEOR\b", re.I)),
    ("CDI", re.compile(r"\bCDI\b|contrat [àa] dur[ée]e ind[ée]termin[ée]e|permanent contract|permanent employment|"
                       r"\bpermanent\b(?= (full|part)-time)", re.I)),
    ("CDD", re.compile(r"\bCDD\b|contrat [àa] dur[ée]e d[ée]termin[ée]e|fixed[- ]term", re.I)),
    ("intérim", re.compile(r"\bint[ée]rim\b|\bMIS\b|mission d.int[ée]rim|temporary agency", re.I)),
    ("full-time employee", re.compile(r"full[- ]time (employee|employment|position|role|job)|\bfull[- ]time\b", re.I)),
    ("part-time employee", re.compile(r"part[- ]time (employee|employment|position|role|job)|temps partiel|\bpart[- ]time\b", re.I)),
]


def tipo_contrato(texto: str) -> str:
    """Devolve o tipo de contrato citado no texto, 'sem contrato (freelance/indépendant)' ou 'não informado'.

    Plataformas de contratação global (Deel/Remote/Oyster): como contractor => sem contrato;
    como employee (EOR) => aceita.
    """
    texto = texto or ""
    eor = TIPOS_CONTRATO[0][1].search(texto) and re.search(r"\bemployee\b|salari[ée]", texto, re.I)
    if SEM_CONTRATO.search(texto) and not eor:
        return "sem contrato (freelance/indépendant)"
    for nome, padrao in TIPOS_CONTRATO:
        if padrao.search(texto):
            if nome == "EOR (employee)" and not eor:
                continue
            return nome
    return "não informado"


def casa(padroes, texto):
    return any(re.search(p, texto, re.I) for p in padroes)


def local_ok(local):
    if not casa(REMOTO, local):
        return False
    # Restrito a outra região, a menos que também cite Europa/EMEA/mundo.
    if casa(REGIAO_RUIM, local) and not casa(REGIAO_OK, local):
        return False
    return True


def main():
    brutas = {}
    for arquivo in sorted(PASTA.glob("vagas-brutas*.json")):
        brutas.update({k: v for k, v in json.loads(arquivo.read_text(encoding="utf-8")).items() if v})
    candidatas = {}
    for empresa, dados in brutas.items():
        lista = [
            v for v in dados["vagas"]
            if not casa(SENIOR_OU_ESTAGIO, v["titulo"])
            and not re.search(OUTRO_IDIOMA, v["titulo"], re.I)
            and local_ok(v["local"] or "")
        ]
        candidatas[empresa] = {"plataforma": dados["plataforma"], "slug": dados["slug"], "total": len(dados["vagas"]), "vagas": lista}
    (PASTA / "vagas-candidatas.json").write_text(json.dumps(candidatas, ensure_ascii=False, indent=1), encoding="utf-8")
    for empresa, dados in candidatas.items():
        print(f"\n## {empresa} {len(dados['vagas'])}/{dados['total']}")
        for v in dados["vagas"][:40]:
            print(f"   - {v['titulo']} | {v['local'][:40]} | {v['link']}")


if __name__ == "__main__":
    main()
