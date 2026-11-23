"""Rodada de pesquisa (sem agente, só script): busca em todas as fontes, triagem completa e entrada na fila.

Uso: python pesquisa/rodada.py
Pode rodar de madrugada (agendamento ainda NÃO ligado, por decisão do candidato: a operação só roda quando ele manda).
Saída: fila/fila.json atualizada e um resumo no terminal. Nada é enviado.
"""

import json
import subprocess
import sys
from pathlib import Path

PASTA = Path(__file__).resolve().parent
sys.path.insert(0, str(PASTA))
import fila as F  # noqa: E402

PY = sys.executable


def etapa(nome, comando):
    print(f"== {nome}")
    r = subprocess.run([PY, *comando], cwd=PASTA.parent, capture_output=True, text=True, encoding="utf-8",
                       env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
    if r.returncode != 0:
        print(r.stdout[-1500:], r.stderr[-1500:])
        raise SystemExit(f"{nome} falhou")
    return r.stdout


def main():
    saida = etapa("busca em todas as fontes", ["pesquisa/busca_diaria.py", "--max", "0"])
    print("\n".join(l for l in saida.splitlines()[:12] if l.strip() and not l.startswith("   ")))
    etapa("triagem (lê a vaga inteira)", ["pesquisa/triagem_detalhada.py", "2000"])
    triadas = json.loads((PASTA / "triagem-detalhada.json").read_text(encoding="utf-8"))

    erros = sum(1 for v in triadas if v.get("erro"))
    if triadas and erros / len(triadas) > 0.6:
        raise SystemExit(f"{erros} de {len(triadas)} vagas sem leitura: provável queda de internet. Fila NÃO alterada; rode de novo.")
    with F.trava():
        _gravar(triadas)


def _gravar(triadas):
    fila = F.carregar()
    novas = 0
    for v in triadas:
        if v.get("erro"):
            status, nota = "ler_no_navegador", f"script não leu: {v['erro'][:60]}"
        elif v.get("barreiras"):
            status, nota = "barrada", "; ".join(b.split(":")[0] for b in v["barreiras"])
        else:
            status, nota = F.rota(v)
            nota = "triagem: " + nota + (" (aviso de idioma)" if v.get("avisos") else "")
        novas += F.incluir(fila, v, status, nota)
    # O que já está na planilha com data de envio fica como "enviada" (nunca mandar duas vezes).
    import csv
    with open(F.RAIZ / "planilha" / "candidaturas.csv", encoding="utf-8") as f:
        enviados = {F.ident(l["link_vaga"]) for l in csv.DictReader(f) if l["data_envio"] and l["link_vaga"]}
    for i in enviados & set(fila):
        if fila[i]["status"] != "enviada":
            F.mudar(fila, i, "enviada", "já consta na planilha")
    F.salvar(fila)
    r = F.resumo(fila)
    print(f"\n{len(triadas)} vagas triadas nesta rodada, {novas} novas na fila.")
    print("Fila: " + ", ".join(f"{s} {r[s]}" for s in F.STATUS if r[s]))


if __name__ == "__main__":
    main()
