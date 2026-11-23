"""Procura e-mails públicos nas páginas de carreiras e contato das empresas.

Só lista o que está escrito no site (regra: nunca inventar endereço).
Uso: python pesquisa/buscar_emails.py
"""

import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor

PAGINAS = {
    "Buffer": ["https://buffer.com/journey", "https://buffer.com/about", "https://buffer.com/contact"],
    "Help Scout": ["https://www.helpscout.com/company/careers/", "https://www.helpscout.com/company/contact/"],
    "Hotjar": ["https://www.hotjar.com/careers/", "https://contentsquare.com/careers/", "https://contentsquare.com/contact/"],
    "Toptal": ["https://www.toptal.com/careers", "https://www.toptal.com/contact"],
    "WeLearn": ["https://welearn.com/careers", "https://welearn.com/contact"],
    "Zapier": ["https://zapier.com/jobs", "https://zapier.com/about"],
    "Automattic": ["https://automattic.com/work-with-us/", "https://automattic.com/contact/"],
    "Aha!": ["https://www.aha.io/company/careers", "https://www.aha.io/company/contact"],
    "Doist": ["https://doist.com/careers", "https://doist.com/contact"],
    "Toggl": ["https://toggl.com/jobs/", "https://toggl.com/contact/"],
    "Remote": ["https://remote.com/careers", "https://remote.com/contact"],
    "Wise": ["https://wise.jobs/", "https://wise.com/help/contact"],
    "Shopify": ["https://www.shopify.com/careers", "https://www.shopify.com/contact"],
    "Basecamp": ["https://basecamp.com/about/jobs", "https://37signals.com/jobs"],
}

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
IGNORAR = re.compile(r"\.(png|jpg|jpeg|gif|svg|webp)$|example\.|sentry|wixpress|@2x|u00", re.I)


def obter(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode("utf-8", "ignore")
    except Exception:
        return ""


def emails(item):
    empresa, urls = item
    achados = {}
    for url in urls:
        for e in set(EMAIL.findall(obter(url))):
            if not IGNORAR.search(e):
                achados.setdefault(e.lower(), url)
    return empresa, achados


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=8) as ex:
        for empresa, achados in ex.map(emails, PAGINAS.items()):
            print(f"## {empresa}: " + ("; ".join(f"{e} ({u})" for e, u in achados.items()) or "nenhum e-mail na página"))
