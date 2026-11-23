"""Gera currículos e pacotes de candidatura (candidaturas/pendentes/*.json) a partir de uma lista.

Uso: python candidaturas/montar_pacotes.py <arquivo de lote .json>
O lote é uma lista de objetos com: id, empresa, vaga, link_vaga, canal, destino, fonte_do_destino, idioma,
subtitulo, mensagem, respostas, motivo, historico_empresa.
"""

import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PY = RAIZ / ".venv" / "Scripts" / "python.exe"
PENDENTES = RAIZ / "candidaturas" / "pendentes"
CVS = RAIZ / "curriculos" / "saida"

lote = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
PENDENTES.mkdir(parents=True, exist_ok=True)
for item in lote:
    cv = CVS / f"CV - {item['empresa']} - {item['id']}.pdf"
    subprocess.run([str(PY), str(RAIZ / "curriculos" / "gerar_curriculo.py"), "--idioma", item["idioma"],
                    "--subtitulo", item["subtitulo"], "--saida", str(cv)], check=True, capture_output=True)
    item["curriculo"] = str(cv)
    destino = PENDENTES / f"{item['id']}.json"
    destino.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    print(destino.relative_to(RAIZ))
