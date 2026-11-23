"""Leitores das APIs oficiais da France Travail (Offres d'emploi v2) e da Adzuna.

As chaves ficam criptografadas em dados/cofre (DPAPI, fora do git) e são lidas só na hora.
francetravail(termos) e adzuna(termos, paises) -> lista de {titulo, empresa, local, link, contrato, descricao, fonte}
Só entram vagas com teletrabalho total (no texto da oferta).
"""

import json
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (job-search script)", "Accept": "application/json"}
TELETRAVAIL_TOTAL = re.compile(
    r"t[ée]l[ée]travail (total|complet|int[ée]gral|100\s?%|à 100\s?%)|100\s?%\s*(en )?t[ée]l[ée]travail|"
    r"full[ -]?remote|fully remote|100\s?%\s*remote|remote[- ]first|enti[èe]rement (en )?t[ée]l[ée]travail|"
    r"poste (en|100\s?%) t[ée]l[ée]travail|work from (home|anywhere)|home[- ]based|à domicile|depuis (votre|ton) domicile|"
    r"remote (position|role|job)|this (is a|role is) (fully )?remote|trabalho remoto|100\s?%\s*remoto", re.I)
TELETRAVAIL_PARCIAL = re.compile(r"t[ée]l[ée]travail partiel|hybrid|hybride|\b[1-4] jours? (de t[ée]l[ée]travail|sur site|au bureau)", re.I)


def chave(nome):
    arq = RAIZ / "dados" / "cofre" / f"{nome}.txt"
    ps = (f"$s = Get-Content '{arq}' | ConvertTo-SecureString; "
          "[Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))")
    return subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, check=True).stdout.strip()


def _json(url, dados=None, cabecalhos=None):
    req = urllib.request.Request(url, data=dados, headers={**UA, **(cabecalhos or {})})
    for tentativa in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                corpo = r.read().decode("utf-8")
                return json.loads(corpo) if corpo.strip() else {}
        except urllib.error.HTTPError as e:
            if e.code == 429 and tentativa < 2:
                time.sleep(3 * (tentativa + 1))
                continue
            raise


def remoto_total(texto):
    return bool(TELETRAVAIL_TOTAL.search(texto)) and not TELETRAVAIL_PARCIAL.search(texto)


# --- France Travail ------------------------------------------------------------------------
FT_TERMOS = ["télétravail", "teletravail", "full remote", "100% remote", "à domicile service client",
             "téléconseiller", "conseiller clientèle", "support client", "support technique", "helpdesk",
             "développeur java", "développeur junior", "portugais", "bilingue anglais", "assistant virtuel",
             "modérateur", "annotation", "transcription", "traducteur", "chargé de clientèle", "téléprospecteur"]


def _ft_token():
    dados = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": chave("francetravail_client_id"),
                                    "client_secret": chave("francetravail_client_secret"),
                                    "scope": "api_offresdemploiv2 o2dsoffre"}).encode()
    r = _json("https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire", dados,
              {"Content-Type": "application/x-www-form-urlencoded"})
    return r["access_token"]


def francetravail(termos=FT_TERMOS, por_termo=150):
    token = _ft_token()
    vistos, saida = set(), []
    for termo in termos:
        for inicio in range(0, por_termo, 150):
            url = ("https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search?"
                   + urllib.parse.urlencode({"motsCles": termo, "range": f"{inicio}-{inicio + 149}"}))
            try:
                r = _json(url, cabecalhos={"Authorization": f"Bearer {token}"})
            except urllib.error.HTTPError as e:
                if e.code in (204, 400, 416):
                    break
                raise
            for o in r.get("resultats", []):
                if o["id"] in vistos:
                    continue
                vistos.add(o["id"])
                texto = f"{o.get('intitule', '')} {o.get('description', '')}"
                if not remoto_total(texto):
                    continue
                contrato = f"{o.get('typeContratLibelle') or o.get('typeContrat', '')} {o.get('natureContrat', '')}".strip()
                saida.append({"titulo": o.get("intitule", ""), "empresa": (o.get("entreprise") or {}).get("nom") or "(não informado)",
                              "local": f"France ({(o.get('lieuTravail') or {}).get('libelle', '')}) remoto",
                              "link": f"https://candidat.francetravail.fr/offres/recherche/detail/{o['id']}",
                              "contrato": contrato, "descricao": o.get("description", ""),
                              "experiencia": o.get("experienceLibelle", ""), "salario": (o.get("salaire") or {}).get("libelle", ""),
                              "fonte": "francetravail-api"})
            if len(r.get("resultats", [])) < 150:
                break
            time.sleep(0.3)
        time.sleep(0.3)
    return saida


# --- Adzuna --------------------------------------------------------------------------------
ADZ_TERMOS = {
    "fr": ["télétravail service client", "télétravail support", "full remote", "100% télétravail", "portugais télétravail",
           "téléconseiller télétravail", "développeur java junior télétravail", "freelance télétravail"],
    "it": ["remote portuguese", "lavoro da remoto francese", "remote customer support french"],
    "pl": ["remote portuguese", "remote french customer support"],
    "gb": ["remote game tester", "remote content moderator", "remote chat support", "remote data entry europe",
           "remote virtual assistant europe", "remote travel consultant", "remote event coordinator",
           "remote customer support french", "remote portuguese", "fully remote customer service", "remote technical support junior",
           "remote junior java developer", "remote data annotation", "remote freelance french"],
    "pt": ["remoto apoio ao cliente", "teletrabalho francês", "remote portuguese french"],
    "es": ["remoto portugués", "teletrabajo francés atención al cliente"],
    "nl": ["remote portuguese", "remote french customer service"],
    "be": ["télétravail service client", "remote portuguese"],
    "de": ["remote portuguese", "remote french customer support"],
}


PAISES = {"it": "Europe (Italy)", "pl": "Europe (Poland)", "fr": "France", "gb": "Europe (United Kingdom)", "pt": "Portugal", "es": "Europe (Spain)", "nl": "Europe (Netherlands)",
          "be": "Europe (Belgium)", "de": "Europe (Germany)"}


def adzuna(termos=ADZ_TERMOS, paginas=2):
    app_id, app_key = chave("adzuna_app_id"), chave("adzuna_app_key")
    vistos, saida = set(), []
    for pais, lista in termos.items():
        for termo in lista:
            for pagina in range(1, paginas + 1):
                url = (f"https://api.adzuna.com/v1/api/jobs/{pais}/search/{pagina}?"
                       + urllib.parse.urlencode({"app_id": app_id, "app_key": app_key, "what": termo,
                                                 "results_per_page": 50, "max_days_old": 14}))
                try:
                    r = _json(url)
                except urllib.error.HTTPError:
                    break
                res = r.get("results", [])
                for o in res:
                    if o["id"] in vistos:
                        continue
                    vistos.add(o["id"])
                    texto = f"{o.get('title', '')} {o.get('description', '')}"
                    if not remoto_total(texto):
                        continue
                    contrato = " ".join(x for x in (o.get("contract_type"), o.get("contract_time")) if x) or "não informado"
                    saida.append({"titulo": re.sub(r"<[^>]+>", "", o.get("title", "")),
                                  "empresa": (o.get("company") or {}).get("display_name", "(não informado)"),
                                  "local": f"{(o.get('location') or {}).get('display_name', '')}, {PAISES[pais]} remoto",
                                  "link": o.get("redirect_url", ""), "contrato": contrato,
                                  "descricao": o.get("description", ""), "fonte": f"adzuna-{pais}"})
                if len(res) < 50:
                    break
                time.sleep(0.4)
    return saida


if __name__ == "__main__":
    import sys
    from collections import Counter
    qual = sys.argv[1] if len(sys.argv) > 1 else "ambas"
    if qual in ("ft", "ambas"):
        v = francetravail()
        print(f"France Travail API: {len(v)} ofertas 100% remotas", Counter(x["contrato"][:20] for x in v).most_common(5))
    if qual in ("adzuna", "ambas"):
        v = adzuna()
        print(f"Adzuna: {len(v)} vagas 100% remotas", Counter(x["fonte"] for x in v))
