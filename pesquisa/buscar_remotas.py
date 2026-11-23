"""Busca vagas remotas em agregadores com consulta pública e aplica a regra principal do candidato.

Fontes: Remotive, Himalayas, RemoteOK, Arbeitnow.
Saída: pesquisa/remotas-candidatas.json, ordenada por encaixe.
Uso: python pesquisa/buscar_remotas.py
"""

import json
import re
import urllib.request
from pathlib import Path

PASTA = Path(__file__).resolve().parent
UA = {"User-Agent": "Mozilla/5.0 (job-search script)", "Accept": "application/json"}

SENIOR = re.compile(r"\b(senior|sr\.?|staff|principal|lead|manager|head|director|vp|vice president|chief|"
                    r"architect|expert|intern(ship)?|trainee|apprentice|alternance|stagiaire)\b", re.I)
REGIAO_OK = re.compile(r"worldwide|anywhere|global|europe|\bEU\b|emea|france|paris|remote$|^remote", re.I)
REGIAO_RUIM = re.compile(r"\b(usa?|united states|us only|canada|latam|latin america|brazil|mexico|india|"
                         r"apac|asia|australia|philippines|africa|uk only)\b", re.I)
ENCAIXE = {
    3: re.compile(r"customer (support|service|success|care|experience)|support (agent|specialist|associate|"
                  r"representative)|help ?desk|technical support|french|portuguese|bilingual|multilingual", re.I),
    2: re.compile(r"\bjunior\b|entry|associate|operations|moderat|virtual assistant|administrative|"
                  r"coordinator|onboarding|community|data entry|video edit|qa tester|java|backend", re.I),
}


def obter(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def remotive():
    vagas = []
    for cat in ["customer-support", "all-others", "admin", "qa", "software-dev"]:
        for v in obter(f"https://remotive.com/api/remote-jobs?category={cat}&limit=150")["jobs"]:
            vagas.append({"fonte": "Remotive", "empresa": v["company_name"], "titulo": v["title"],
                          "local": v.get("candidate_required_location", ""), "link": v["url"],
                          "data": v.get("publication_date", "")[:10]})
    return vagas


def himalayas():
    vagas = []
    for offset in (0, 20, 40, 60, 80):
        for v in obter(f"https://himalayas.app/jobs/api?limit=20&offset={offset}").get("jobs", []):
            loc = ", ".join(v.get("locationRestrictions") or []) or "Worldwide"
            vagas.append({"fonte": "Himalayas", "empresa": v.get("companyName", ""), "titulo": v.get("title", ""),
                          "local": loc, "link": v.get("applicationLink") or v.get("guid", ""),
                          "data": str(v.get("pubDate", ""))[:10]})
    return vagas


def remoteok():
    vagas = []
    for v in obter("https://remoteok.com/api")[1:]:
        vagas.append({"fonte": "RemoteOK", "empresa": v.get("company", ""), "titulo": v.get("position", ""),
                      "local": v.get("location", "") or "Worldwide", "link": v.get("apply_url") or v.get("url", ""),
                      "data": v.get("date", "")[:10]})
    return vagas


def arbeitnow():
    vagas = []
    for v in obter("https://www.arbeitnow.com/api/job-board-api")["data"]:
        if v.get("remote"):
            vagas.append({"fonte": "Arbeitnow", "empresa": v["company_name"], "titulo": v["title"],
                          "local": v.get("location", "") + " (remoto)", "link": v["url"], "data": ""})
    return vagas


def nota(v):
    for pontos, padrao in ENCAIXE.items():
        if padrao.search(v["titulo"]):
            return pontos
    return 1


def main():
    todas = []
    for fonte in (remotive, himalayas, remoteok, arbeitnow):
        try:
            todas += fonte()
        except Exception as e:
            print(f"{fonte.__name__}: falhou ({e})")
    candidatas, vistos = [], set()
    for v in todas:
        chave = (v["empresa"].lower(), v["titulo"].lower())
        if chave in vistos or SENIOR.search(v["titulo"]):
            continue
        vistos.add(chave)
        local = v["local"] or "Worldwide"
        if REGIAO_RUIM.search(local) and not REGIAO_OK.search(local):
            continue
        if not REGIAO_OK.search(local) and "remoto" not in local:
            continue
        v["encaixe"] = nota(v)
        candidatas.append(v)
    candidatas.sort(key=lambda v: (-v["encaixe"], v["data"]), reverse=False)
    (PASTA / "remotas-candidatas.json").write_text(json.dumps(candidatas, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(todas)} vagas lidas, {len(candidatas)} passaram no filtro")
    for v in candidatas[:45]:
        print(f"[{v['encaixe']}] {v['empresa']} | {v['titulo']} | {v['local'][:35]} | {v['fonte']} | {v['link'][:80]}")


if __name__ == "__main__":
    main()
