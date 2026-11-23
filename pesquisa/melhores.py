"""Mostra as N melhores candidatas da lista do dia nas categorias de foco (sem 'outro').

Uso: python pesquisa/melhores.py [N]
"""

import json
import sys
from collections import Counter
from pathlib import Path

n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
dados = json.loads((Path(__file__).resolve().parent / "lista-do-dia.json").read_text(encoding="utf-8"))
lista = dados["candidatas"]
foco = [v for v in lista if v["categoria"] != "outro"]
print(f"{dados['total_lidas']} vagas lidas, {len(lista)} candidatas ({len(foco)} nas categorias de foco)")
print("Por categoria:", dict(Counter(v["categoria"] for v in lista)))
print("Por fonte:    ", dict(Counter(v["fonte"] for v in lista)))
print(f"\n{n} melhores (categoria | empresa | vaga | contrato | link):")
for i, v in enumerate(foco[:n], 1):
    print(f"{i:2} {v['categoria']:15} | {v['empresa'][:22]} | {v['titulo'][:58]} | {v['contrato'][:15]} | {v['link']}")
