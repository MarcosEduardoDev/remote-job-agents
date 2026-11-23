"""Checagem local de um pacote ANTES do verificador (pega os erros que mais reprovaram pacotes).

Uso: python verificacao/checar_pacote.py candidaturas/pendentes/<id>.json
Sai com código 0 (OK) ou 1 (lista de problemas). Não substitui o verificador: só evita viagens perdidas.
"""

import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PY = sys.executable
CAMPOS = ["empresa", "vaga", "link_vaga", "canal", "destino", "fonte_do_destino", "idioma", "subtitulo", "curriculo",
          "mensagem", "respostas", "motivo", "historico_empresa", "categoria", "contrato"]
# Frases que já reprovaram pacotes por não terem fonte, e declarações de nível proibidas (INSTRUCOES.md).
PROIBIDAS = [
    (r"\b(C1|C2)\b", "declara nível C1/C2"),
    (r"\b(native|natif|native-level|nativo)\b", "declara nativo em idioma que não é o português"),
    (r"\bfluent (in )?(english|french)|(english|french) fluent|fran[cç]ais courant|anglais courant|bilingue anglais", "declara fluência"),
    (r"\b\d+\+? (years|ans|anos)\b", "cita anos de experiência"),
    (r"certif|bachelor|licence|dipl[oô]m|degree", "cita certificado ou diploma"),
    (r"calm under|sang-froid|calme sous", "qualidade sem fonte no currículo"),
    (r"explain(ing)? technical steps|plain language", "habilidade sem fonte no currículo"),
    (r"voyager|travel across|déplacements", "disponibilidade para viagens: só se a vaga pedir (decisão de 2026-11-21)"),
]
STOP = {"en": r"\b(the|and|i am|with|for|my)\b", "fr": r"\b(le|la|les|et|je|avec|pour|mon)\b", "pt": r"\b(o|a|os|e|com|para|meu|na)\b"}


def problemas(p):
    erros = [f"campo faltando: {c}" for c in CAMPOS if c not in p or p[c] in (None, "")
             and c not in ("mensagem",)]
    msg, idioma = p.get("mensagem", ""), p.get("idioma", "")
    dados = json.loads((RAIZ / "dados" / "dados-formulario.json").read_text(encoding="utf-8"))
    texto_dados = json.dumps(dados, ensure_ascii=False)

    cv = Path(p.get("curriculo", ""))
    if not cv.exists():
        erros.append("currículo não existe")
    else:
        import os
        r = subprocess.run([PY, str(RAIZ / "verificacao" / "verificar_curriculo.py"), str(cv), idioma],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
        if "OK" not in r.stdout:
            erros.append("verificar_curriculo não deu OK: " + r.stdout.strip()[-150:])

    if msg:
        contagem = {k: len(re.findall(v, msg.lower())) for k, v in STOP.items()}
        if max(contagem, key=contagem.get) != idioma:
            erros.append(f"mensagem não parece estar em '{idioma}' ({contagem})")
        if p.get("empresa", "").split()[0].lower() not in msg[:400].lower():
            erros.append("a mensagem não cita a empresa no começo")
        if "{" in msg:
            erros.append("sobrou marcador {..} do modelo na mensagem")
    for padrao, motivo in PROIBIDAS:
        alvo = msg + " " + json.dumps(p.get("respostas", {}), ensure_ascii=False) + " " + p.get("subtitulo", "")
        # Português nativo é verdade (frases dos modelos aprovados): tira antes de procurar "native/natif/nativo".
        alvo = re.sub(r"native portuguese|portugais natif|portugu[eê]s nativo|portuguese is my native language|"
                      r"portuguese \(native\)|portugais \(natif\)|portugu[eê]s \(nativo\)|portugu[eê]s é minha língua nativa",
                      "", alvo, flags=re.I)
        if re.search(padrao, alvo, re.I):
            if motivo.startswith("disponibilidade para viagens") and re.search(r"voyag|travel|déplacement|viage", p.get("motivo", ""), re.I):
                continue
            erros.append(f"{motivo}: '{re.search(padrao, alvo, re.I).group(0)}'")

    for k, v in (p.get("respostas") or {}).items():
        val = str(v)
        digitos = re.sub(r"\D", "", val)
        # Só campos de telefone (link do LinkedIn e datas também têm muitos dígitos).
        if re.search(r"phone|t[ée]l[ée]phone|telefone|mobile|portable|whatsapp", k, re.I) and len(digitos) >= 8 \
                and not digitos.endswith("000000000"):
            erros.append(f"telefone diferente dos dados em '{k}'")
        if "@" in val and "candidato@example.com" not in val:
            erros.append(f"e-mail diferente dos dados em '{k}'")

    if p.get("canal") == "email" and not re.fullmatch(r"[^@\s]+@[^@\s]+\.\w+", p.get("destino", "")):
        erros.append("canal e-mail sem endereço válido em 'destino'")

    # 1 candidatura por empresa a cada 90 dias (mesma vaga nunca), no máximo 2 por rodada.
    limite = datetime.now() - timedelta(days=90)
    with open(RAIZ / "planilha" / "candidaturas.csv", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            if linha["empresa"].strip().lower() == p.get("empresa", "").strip().lower() and linha["data_envio"]:
                if linha["link_vaga"] and linha["link_vaga"].split("?")[0] == p.get("link_vaga", "").split("?")[0]:
                    erros.append("esta vaga já foi enviada antes")
                elif datetime.strptime(linha["data_envio"], "%d/%m/%Y") >= limite:
                    erros.append(f"empresa já recebeu candidatura em {linha['data_envio']} (regra dos 90 dias: avisar no histórico)")
    if "candidato@example.com" not in texto_dados:
        erros.append("dados-formulario.json sem o e-mail esperado")
    return erros


def main():
    p = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    erros = problemas(p)
    if erros:
        print("PROBLEMAS:")
        for e in erros:
            print(" -", e)
        raise SystemExit(1)
    print("OK: pacote pronto para o verificador")


if __name__ == "__main__":
    main()
