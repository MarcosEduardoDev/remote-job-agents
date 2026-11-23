"""Relatório das vagas fora da lista branca (categoria "outro" ou dev/Account Executive não júnior), para o candidato
revisar por amostragem. Não vão para o redator (decisão de 2026-11-22).

Uso: python pesquisa/fora_lista.py
Saída: relatorios/fora-da-lista.csv (título, empresa, link, motivo) a partir da última triagem.
"""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from categorias import categorizar, na_lista_branca  # noqa: E402

PASTA = Path(__file__).resolve().parent


def main():
    triadas = json.loads((PASTA / "triagem-detalhada.json").read_text(encoding="utf-8"))
    fora = []
    for v in triadas:
        cat = categorizar(v.get("titulo", ""), "", None)
        if not na_lista_branca(cat, v.get("titulo")):
            motivo = "outro" if cat == "outro" else f"{cat} sem nível júnior"
            fora.append([v.get("titulo"), v.get("empresa"), v.get("destino") or v.get("link"), motivo])
    saida = PASTA.parent / "relatorios" / "fora-da-lista.csv"
    saida.parent.mkdir(exist_ok=True)
    with open(saida, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Vaga", "Empresa", "Link", "Motivo"])
        w.writerows(sorted(fora, key=lambda x: (x[3], x[1] or "")))
    print(f"{len(fora)} de {len(triadas)} vagas fora da lista branca -> {saida}")


if __name__ == "__main__":
    main()
