"""Exporta a Fila manual (vagas que passaram na triagem mas não são da fila automática) para a planilha.

Uso: python pesquisa/fila_manual.py
Saída: relatorios/fila-manual.csv, ordenado por prioridade (Normal antes de Baixa; Baixa = veio de agregador como a
Adzuna) e por área. O orquestrador copia o CSV para a aba "Fila manual" da planilha Google.
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fila as F  # noqa: E402

ORDEM_AREA = ["atendimento", "games", "suporte_tecnico", "dados_ia", "dev", "outro"]
NOME_AREA = {"atendimento": "Atendimento", "games": "Games", "suporte_tecnico": "Suporte técnico",
             "dados_ia": "Dados para IA", "dev": "Desenvolvimento", "outro": "Outras áreas"}


def main():
    fila = F.carregar()
    itens = [e for e in fila.values() if e["status"] == "manual"]
    itens.sort(key=lambda e: (e.get("prioridade_manual") == "Baixa",
                              ORDEM_AREA.index(e.get("categoria")) if e.get("categoria") in ORDEM_AREA else 9,
                              e.get("empresa") or ""))
    saida = F.RAIZ / "relatorios" / "fila-manual.csv"
    saida.parent.mkdir(exist_ok=True)
    with open(saida, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Feito", "Prioridade", "Empresa", "Vaga", "Área", "Por que é manual", "Link para se candidatar", "Desde"])
        for e in itens:
            w.writerow(["FALSE", e.get("prioridade_manual", "Normal"), e.get("empresa"), e.get("titulo"),
                        NOME_AREA.get(e.get("categoria"), "Outras áreas"), e.get("motivo_manual", ""),
                        e.get("destino") or e.get("link"), (e.get("atualizado") or "")[:10]])
    print(f"{len(itens)} vagas na fila manual -> {saida}")


if __name__ == "__main__":
    main()
