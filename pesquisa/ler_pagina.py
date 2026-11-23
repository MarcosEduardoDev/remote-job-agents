"""Baixa uma página pública e mostra só as linhas com termos relevantes (requisitos, local, link de candidatura).

Uso: python pesquisa/ler_pagina.py <url> [max linhas]
"""

import html
import re
import sys
import urllib.request

TERMOS = re.compile(r"year|experience|required|must|fluent|english|french|portugu|location|remote|anywhere|"
                    r"worldwide|europe|time ?zone|hours|training|junior|entry|contract|freelance|salary|\$|€|"
                    r"apply|application|degree|based in|countr", re.I)

url = sys.argv[1]
limite = int(sys.argv[2]) if len(sys.argv) > 2 else 25
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
bruto = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
links = sorted(set(re.findall(r'href="(https?://[^"]*(?:apply|greenhouse|lever|ashby|workable|recruitee|bamboohr|'
                              r'breezy|jobs\.|careers)[^"]*)"', bruto)))[:6]
texto = html.unescape(re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", bruto, flags=re.S))
texto = re.sub(r"<(br|/p|/li|/h\d|/div)[^>]*>", "\n", texto)
texto = re.sub(r"<[^>]+>", " ", texto)
linhas = [re.sub(r"\s+", " ", l).strip() for l in texto.splitlines()]
vistas = []
for l in linhas:
    if 15 < len(l) < 260 and TERMOS.search(l) and l not in vistas:
        vistas.append(l)
print(f"### {url}")
print("\n".join(vistas[:limite]))
print("LINKS:", " | ".join(links))
