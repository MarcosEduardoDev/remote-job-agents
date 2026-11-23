"""Vagas que chegam pelos alertas de e-mail (Welcome to the Jungle, hiring.cafe, Indeed, HelloWork, LinkedIn).

Fluxo (decisão do candidato, 2026-11-23): os sites bloqueiam robôs, mas mandam alertas para o e-mail do candidato.
O agente leitor abre o Outlook web, lê os alertas novos e grava uma linha por vaga num arquivo:
    titulo | empresa | local | link | site
Este script coloca cada vaga na fila com status ler_no_navegador (o leitor abre a vaga, acha o formulário
final e aplica as barreiras). O filtro de local e a lista branca valem antes de qualquer leitura.

Uso: python pesquisa/alertas.py <arquivo.txt>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fila as F  # noqa: E402


def main():
    linhas = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    novas = 0
    with F.trava():
        f = F.carregar()
        for linha in linhas:
            partes = [p.strip() for p in linha.split("|")]
            if len(partes) < 4 or not partes[3].startswith("http"):
                continue
            titulo, empresa, local, link = partes[:4]
            site = partes[4] if len(partes) > 4 else "alerta"
            v = {"titulo": titulo, "empresa": empresa, "local": local, "link": link, "destino": "",
                 "fonte": f"alerta-{site}"}
            st, nota = F.rota(dict(v, link=link))
            if st == "manual":  # destino ainda desconhecido: o leitor precisa abrir a vaga
                st, nota = "ler_no_navegador", f"alerta de e-mail ({site}): o leitor abre a vaga e acha o formulário"
            if F.incluir(f, v, st, nota):
                novas += 1
                print(f"{st:16} | {empresa[:20]:20} | {titulo[:50]}")
        F.salvar(f)
    print(f"{novas} vagas novas dos alertas")


if __name__ == "__main__":
    main()
