"""Lê a descrição de uma vaga (Greenhouse, Ashby, Workable ou Lever) e imprime o texto limpo.

Uso: python pesquisa/ler_vaga.py <link da vaga> [limite de caracteres]
"""

import html
import json
import re
import sys
import urllib.request


def obter(url, texto=False):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        dados = r.read().decode("utf-8")
    return dados if texto else json.loads(dados)


def limpar(conteudo):
    conteudo = html.unescape(conteudo)
    conteudo = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", conteudo)
    conteudo = re.sub(r"<li[^>]*>", "- ", conteudo)
    conteudo = re.sub(r"<[^>]+>", "", conteudo)
    return re.sub(r"\n\s*\n+", "\n", conteudo).strip()


def ler(link):
    if m := re.search(r"greenhouse\.io/([^/]+)/jobs/(\d+)", link):
        eu = ".eu" if "eu.greenhouse" in link else ""
        d = obter(f"https://boards-api{eu}.greenhouse.io/v1/boards/{m[1]}/jobs/{m[2]}?questions=true")
        perguntas = [q["label"] + (" *" if q.get("required") else "") for q in d.get("questions", [])]
        return d["title"], d["location"]["name"], limpar(d["content"]), perguntas
    if m := re.search(r"ashbyhq\.com/([^/]+)/([0-9a-f-]{36})", link):
        d = obter(f"https://api.ashbyhq.com/posting-api/job-board/{m[1]}")
        v = next(j for j in d["jobs"] if j["id"] == m[2])
        return v["title"], v.get("location", ""), limpar(v.get("descriptionHtml", "")), []
    if m := re.search(r"workable\.com/(?:([a-z0-9-]+)/)?j/([0-9A-F]+)", link):
        conta = m[1] or (sys.argv[3] if len(sys.argv) > 3 else "crossbordertalents")
        d = obter(f"https://apply.workable.com/api/v2/accounts/{conta}/jobs/{m[2]}")
        loc = d.get("location", {})
        texto = limpar(d.get("description", "") + d.get("requirements", "") + d.get("benefits", ""))
        return d["title"], f'{loc.get("city")} {loc.get("country")} remoto={d.get("remote")} tipo={d.get("workplace")}', texto, []
    if m := re.search(r"lever\.co/([^/]+)/([0-9a-f-]{36})", link):
        d = obter(f"https://api.lever.co/v0/postings/{m[1]}/{m[2]}")
        return d["text"], d["categories"].get("location", ""), d.get("descriptionPlain", "") + "\n" + "\n".join(l["text"] + ": " + limpar(l["content"]) for l in d.get("lists", [])), []
    raise SystemExit(f"plataforma não reconhecida: {link}")


if __name__ == "__main__":
    limite = int(sys.argv[2]) if len(sys.argv) > 2 else 3500
    titulo, local, texto, perguntas = ler(sys.argv[1])
    print(f"### {titulo} | {local}\n{texto[:limite]}")
    if perguntas:
        print("\nPERGUNTAS DO FORMULÁRIO:", " | ".join(perguntas))
