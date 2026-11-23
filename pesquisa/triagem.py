"""Aplica o filtro da regra principal a um arquivo de vagas brutas e mostra as candidatas,
com as de suporte/atendimento/idiomas/entrada primeiro.

Uso: python pesquisa/triagem.py <vagas-brutas.json> [max]
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from filtrar_vagas import OUTRO_IDIOMA, SENIOR_OU_ESTAGIO, casa, local_ok  # noqa: E402

PRIORIDADE = re.compile(r"support|customer|client|success|service|care|help|french|portugu|brazil|bilingual|"
                        r"junior|entry|associate|operations|moderat|assistant|coordinator|onboarding|community|"
                        r"specialist|agent|analyst", re.I)

brutas = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
limite = int(sys.argv[2]) if len(sys.argv) > 2 else 60
saida = []
for empresa, dados in brutas.items():
    for v in dados["vagas"]:
        if casa(SENIOR_OU_ESTAGIO, v["titulo"]) or re.search(OUTRO_IDIOMA, v["titulo"], re.I):
            continue
        if not local_ok(v["local"] or ""):
            continue
        saida.append((0 if PRIORIDADE.search(v["titulo"]) else 1, empresa, v))
saida.sort(key=lambda x: (x[0], x[1]))
print(len(saida), "candidatas")
for p, empresa, v in saida[:limite]:
    print(f"{'*' if p == 0 else ' '} {empresa} | {v['titulo']} | {v['local'][:40]} | {v['link']}")
