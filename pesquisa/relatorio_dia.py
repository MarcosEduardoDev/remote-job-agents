"""Relatório do dia: o que foi enviado, o que respondeu e a fila "falta só você" (o que depende do candidato).

Uso: python pesquisa/relatorio_dia.py [AAAA-MM-DD]
Saída: relatorios/<data>.md e relatorios/<data>-falta-voce.csv (este vai para a aba "Falta você" da planilha).
"""

import csv
import json
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fila as F  # noqa: E402

RAIZ = F.RAIZ
SAIDA = RAIZ / "relatorios"


def main():
    dia = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    dia_br = datetime.strptime(dia, "%Y-%m-%d").strftime("%d/%m/%Y")
    fila = F.carregar()
    r = F.resumo(fila)

    def mudou_hoje(e, status):
        return any(h["status"] == status and h["quando"].startswith(dia) for h in e.get("historico", []))

    enviadas_hoje = [e for e in fila.values() if mudou_hoje(e, "enviada")]
    with open(RAIZ / "planilha" / "candidaturas.csv", encoding="utf-8") as f:
        planilha_hoje = [l for l in csv.DictReader(f) if l["data_envio"] == dia_br]
    falta = sorted((e for e in fila.values() if e["status"] == "falta_voce"), key=lambda e: e.get("atualizado", ""))
    reprovadas = [e for e in fila.values() if e["status"] == "reprovada"]
    pulou = Counter((e.get("historico") or [{}])[-1].get("nota", "")[:60] for e in fila.values()
                    if e["status"] == "pulada" and mudou_hoje(e, "pulada"))
    barrou = Counter(b.split(":")[0] for e in fila.values() if mudou_hoje(e, "barrada") for b in e.get("barreiras") or [])

    L = [f"# Relatório de {dia_br}", "",
         f"**Enviadas hoje:** {len(planilha_hoje)} (planilha) · **Na fila:** " + ", ".join(f"{s} {r[s]}" for s in F.STATUS if r[s]), ""]
    L += ["## Falta só você", ""]
    if falta:
        L += ["| Empresa | Vaga | O que falta | Link |", "|---|---|---|---|"]
        for e in falta:
            nota = (e.get("historico") or [{}])[-1].get("nota", "")
            L.append(f"| {e['empresa']} | {e['titulo']} | {nota} | {e.get('destino') or e['link']} |")
    else:
        L.append("Nada pendente.")
    L += ["", "## Enviadas hoje", ""]
    L += [f"- {l['empresa']}: {l['vaga']} ({l['canal']})" for l in planilha_hoje] or ["Nenhuma."]
    L += ["", "## Reprovadas pelo verificador (aguardando correção)", ""]
    L += [f"- {e['empresa']}: {e['titulo']} — {(e.get('historico') or [{}])[-1].get('nota', '')}" for e in reprovadas] or ["Nenhuma."]
    L += ["", "## Por que vagas caíram hoje", "", "Barreiras da triagem: " + (", ".join(f"{k} {v}" for k, v in barrou.most_common()) or "nenhuma"),
          "Puladas pelo redator/leitor: " + (", ".join(f"{k} ({v})" for k, v in pulou.most_common(8)) or "nenhuma")]

    SAIDA.mkdir(exist_ok=True)
    (SAIDA / f"{dia}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    with open(SAIDA / f"{dia}-falta-voce.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Empresa", "Vaga", "O que falta", "Link", "Desde"])
        for e in falta:
            w.writerow([e["empresa"], e["titulo"], (e.get("historico") or [{}])[-1].get("nota", ""),
                        e.get("destino") or e["link"], e.get("atualizado", "")])
    print("\n".join(L))


if __name__ == "__main__":
    main()
