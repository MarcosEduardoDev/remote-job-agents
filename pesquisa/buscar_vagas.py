"""Busca as vagas abertas das empresas nas plataformas de recrutamento que têm consulta pública
(Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee, Personio).

Para cada empresa testa os nomes prováveis em cada plataforma e guarda as vagas encontradas
em pesquisa/vagas-brutas.json. Empresas sem resultado precisam ser vistas no site.

Uso: python pesquisa/buscar_vagas.py
"""

import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PASTA = Path(__file__).resolve().parent

EMPRESAS = {
    "Automattic": ["automatticcareers"],
    "Aha!": [],  # site próprio: aha.io/company/careers/current-openings
    "Casafari": ["casafari"],
    "Canonical": ["canonical"],
    "WeLearn": ["welearn"],
    "Aircall": ["aircallioinc"],
    "Cross Border Talents": ["crossbordertalents", "cross-border-talents", "cbt"],
    "Zapier": ["zapier"],
    "Doist": ["doist"],
    "Buffer": ["buffer"],
    "Help Scout": ["helpscout", "help-scout"],
    "Hotjar": ["contentsquare"],
    "Toggl": ["toggl"],
    "GitLab": ["gitlab"],
    "Remote": [],  # site próprio: remote.com/openings
    "Wise": [],  # site próprio: wise.jobs
    "Booking.com": [],  # site próprio: jobs.booking.com
    "Shopify": [],  # site próprio: shopify.com/careers
    "Toptal": ["toptal"],
    "Basecamp": [],  # site próprio: basecamp.com/about/jobs
}


def obter(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


def greenhouse(slug):
    dados = obter(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
    return [{"titulo": v["title"], "local": (v.get("location") or {}).get("name", ""), "link": v["absolute_url"]} for v in dados["jobs"]]


def lever(slug):
    dados = obter(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    return [{"titulo": v["text"], "local": (v.get("categories") or {}).get("location", "") + " " + (v.get("workplaceType") or ""), "link": v["hostedUrl"]} for v in dados]


def ashby(slug):
    dados = obter(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    return [{"titulo": v["title"], "local": f'{v.get("location", "")} {"remoto" if v.get("isRemote") else ""}'.strip(), "link": v["jobUrl"]} for v in dados["jobs"]]


def workable(slug):
    dados = obter(f"https://apply.workable.com/api/v1/widget/accounts/{slug}")
    return [{"titulo": v["title"], "local": f'{v.get("city", "")} {v.get("country", "")} {"remoto" if v.get("telecommuting") else ""}'.strip(), "link": v["url"]} for v in dados["jobs"]]


def smartrecruiters(slug):
    dados = obter(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100")
    return [{"titulo": v["name"], "local": f'{v["location"].get("city", "")} {v["location"].get("country", "")} {"remoto" if v["location"].get("remote") else ""}'.strip(), "link": f'https://jobs.smartrecruiters.com/{slug}/{v["id"]}'} for v in dados["content"]]


def recruitee(slug):
    dados = obter(f"https://{slug}.recruitee.com/api/offers/")
    return [{"titulo": v["title"], "local": f'{v.get("location", "")} {"remoto" if v.get("remote") else ""}'.strip(), "link": v["careers_url"]} for v in dados["offers"]]


PLATAFORMAS = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "workable": workable,
    "smartrecruiters": smartrecruiters,
    "recruitee": recruitee,
}


def buscar_empresa(item):
    empresa, slugs = item
    for slug in slugs:
        for nome, funcao in PLATAFORMAS.items():
            try:
                vagas = funcao(slug)
            except Exception:
                continue
            if vagas:
                return empresa, {"plataforma": nome, "slug": slug, "vagas": vagas}
    return empresa, None


def main():
    with ThreadPoolExecutor(max_workers=10) as executor:
        resultado = dict(executor.map(buscar_empresa, EMPRESAS.items()))
    (PASTA / "vagas-brutas.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    for empresa, dados in resultado.items():
        if dados:
            print(f"{empresa:22} {dados['plataforma']:15} {len(dados['vagas']):4} vagas")
        else:
            print(f"{empresa:22} -- sem plataforma pública, ver no site")


if __name__ == "__main__":
    main()
