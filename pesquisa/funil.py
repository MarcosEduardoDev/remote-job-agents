"""Funil da busca do dia: em que filtro cada vaga bruta foi descartada.

Uso: python pesquisa/funil.py
Lê pesquisa/vagas-brutas-dia.json (gravado pela busca_diaria.py) e mostra, por fonte, quantas vagas
caem em cada etapa, na mesma ordem dos filtros de busca_diaria.passa.
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import busca_diaria as bd  # noqa: E402

PASTA = Path(__file__).resolve().parent


def motivo(v):
    t, local, emp, ct = v["titulo"], v.get("local") or "", v.get("empresa", ""), v.get("contrato", "")
    if __import__("re").search(r"commission[- ]only", t + " " + (ct or ""), __import__("re").I):
        return "1 só comissão"
    if bd.RESIDENCIA_LATAM.search(t + " " + local):
        return "2 exige residência LATAM"
    if bd.EMPRESAS_SEM_IA.search(emp) or bd.EMPRESAS_ENTREVISTA_IA.search(emp):
        return "3 empresa bloqueada"
    if bd.SENIOR_OU_ESTAGIO.search(bd.MANAGER_CLIENTE.sub(" ", t)):
        return "4 sênior/chefia/estágio"
    if bd.OUTRO_IDIOMA.search(t):
        return "5 outro idioma no título"
    if bd.RELOCACAO.search(t):
        return "6 experiente/relocação"
    if not bd.REMOTO.search(local + " " + t):
        return "7 não remota"
    if not bd.passa(t, local, emp, ct):
        return "8 região fora (EUA, APAC, LATAM...)"
    return "9 passou nos filtros"


def main():
    brutas = json.loads((PASTA / "vagas-brutas-dia.json").read_text(encoding="utf-8"))
    total = Counter()
    por_fonte = defaultdict(Counter)
    for v in brutas:
        m = motivo(v)
        total[m] += 1
        por_fonte[v.get("fonte", "?")][m] += 1
    print(f"Vagas brutas: {len(brutas)}")
    for m in sorted(total):
        print(f"  {m:38} {total[m]:6}  ({100 * total[m] / len(brutas):4.1f}%)")
    print("\nPor fonte (brutas -> passaram):")
    for f, c in sorted(por_fonte.items(), key=lambda x: -sum(x[1].values())):
        print(f"  {f:16} {sum(c.values()):6} -> {c['9 passou nos filtros']}")


if __name__ == "__main__":
    main()
