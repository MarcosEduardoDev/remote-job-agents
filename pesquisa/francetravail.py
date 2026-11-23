"""Leitor do site público de ofertas da France Travail (candidat.francetravail.fr).

O robots.txt permite a busca de ofertas. O leitor faz poucas requisições, com pausa entre elas, e só
confirma "teletrabalho total" abrindo o detalhe das ofertas que citam teletrabalho.

buscar(termos) -> lista de {titulo, local, link, empresa, contrato, fonte}
"""

import html
import re
import time
import urllib.parse
import urllib.request

BASE = "https://candidat.francetravail.fr"
UA = {"User-Agent": "Mozilla/5.0 (job-search script)"}
TERMOS = ["conseiller client télétravail", "chargé de clientèle télétravail", "support client portugais",
          "support client bilingue", "support technique N1 télétravail", "téléconseiller portugais",
          "customer support portuguese", "player support",
          # termos que de fato trazem teletrabalho total (testados em 2026-11-21)
          "télétravail 100%", "100% télétravail service client", "100% télétravail support", "télétravail complet",
          "full remote",
          # ampliação de 2026-11-22 (o candidato entrou na conta France Travail no navegador do Orca)
          "téléconseiller télétravail", "téléconseiller 100% télétravail", "conseiller clientèle 100% télétravail",
          "service client à domicile", "télétravail total", "télétravail intégral", "100% remote",
          "support informatique télétravail", "helpdesk télétravail", "technicien support 100% télétravail",
          "développeur java télétravail", "développeur junior télétravail", "anglais télétravail 100%",
          "portugais télétravail", "bilingue anglais télétravail", "assistant administratif télétravail",
          "chargé de relation client télétravail", "modérateur télétravail", "service client anglais télétravail",
          # ampliação de 2026-11-23 (o candidato: "pode continuar pela France Travail")
          "conseiller vente à distance télétravail", "téléprospecteur télétravail", "télévendeur télétravail",
          "chargé de recrutement télétravail", "sourceur télétravail", "assistant commercial télétravail",
          "conseiller voyage télétravail", "agent de réservation télétravail", "community manager télétravail",
          "testeur jeux vidéo", "testeur QA télétravail", "support clientèle espagnol portugais",
          "chargé de support télétravail", "customer success télétravail", "account manager télétravail",
          "business developer junior télétravail", "SDR télétravail", "annotateur données",
          "traducteur portugais", "rédacteur web télétravail", "assistant virtuel télétravail",
          "standardiste télétravail", "gestionnaire de dossiers télétravail", "conseiller relation client domicile"]
CITA_TELETRAVAIL = re.compile(r"t[ée]l[ée]travail|remote|full remote|à distance depuis (votre|ton) domicile|home office", re.I)
TELETRAVAIL_TOTAL = re.compile(r"t[ée]l[ée]travail (total|complet|int[ée]gral|100\s?%|à 100)|100\s?%\s*(en )?t[ée]l[ée]travail|"
                               r"full[ -]remote|fully remote|100\s?%\s*remote|enti[èe]rement (en )?t[ée]l[ée]travail|"
                               r"poste (en|100\s?%) t[ée]l[ée]travail", re.I)


def _baixar(url):
    time.sleep(1.0)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
        return r.read().decode("utf-8", "ignore")


def _texto(trecho):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", trecho)))


def _resultados(termo, paginas=2):
    ofertas = []
    for p in range(paginas):
        url = (f"{BASE}/offres/recherche?motsCles={urllib.parse.quote_plus(termo)}"
               f"&offresPartenaires=true&tri=0&range={p * 20}-{p * 20 + 19}")
        try:
            pagina = _baixar(url)
        except Exception:
            break
        blocos = re.findall(r"<li[^>]*data-id-offre=\"([^\"]+)\"(.*?)</li>", pagina, re.S)
        for ident, corpo in blocos:
            corpo = corpo.split(">", 1)[1] if ">" in corpo else corpo  # tira o resto da tag <li ...>
            partes = [p.strip() for p in _texto(corpo).split("|") if p.strip() and p.strip() != "(déjà vu)"]
            if len(partes) < 3:
                continue
            titulo, empresa_local = partes[0], partes[1] if len(partes) > 1 else ""
            empresa, _, local = empresa_local.partition(" - ")
            if not local and len(partes) > 2:
                local = partes[2]
            contrato = next((x for x in partes if re.match(r"(CDI|CDD|MIS|Int[ée]rim|Contrat|Saisonnier|Ind[ée]pendant|Franchise|Lib[ée]ral)", x)), "não informado")
            resumo = " ".join(partes[2:6])
            ofertas.append({"id": ident, "titulo": titulo, "empresa": empresa.strip() or "(não informado)",
                            "cidade": local.strip(), "contrato": contrato, "resumo": resumo,
                            "link": f"{BASE}/offres/recherche/detail/{ident}"})
        if len(blocos) < 20:
            break
    return ofertas


def buscar(termos=TERMOS, paginas=2):
    vistos, saida = set(), []
    for termo in termos:
        for o in _resultados(termo, paginas):
            if o["id"] in vistos:
                continue
            vistos.add(o["id"])
            if not CITA_TELETRAVAIL.search(o["titulo"] + " " + o["resumo"]):
                continue
            try:
                detalhe = _texto(_baixar(o["link"]))
            except Exception:
                continue
            if not TELETRAVAIL_TOTAL.search(detalhe):
                continue  # teletrabalho parcial/híbrido: fica de fora
            m = re.search(r"Type de contrat\s*\|?\s*([^|]{3,60})", detalhe)
            contrato = (m.group(1).strip() if m else o["contrato"])
            saida.append({"titulo": o["titulo"], "empresa": o["empresa"], "local": f"France ({o['cidade']}) remoto",
                          "link": o["link"], "contrato": contrato, "fonte": "francetravail"})
    return saida


if __name__ == "__main__":
    for v in buscar(paginas=1):
        print(f"{v['empresa'][:25]} | {v['titulo'][:60]} | {v['local'][:35]} | {v['contrato'][:25]} | {v['link']}")
