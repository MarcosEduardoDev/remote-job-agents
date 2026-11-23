"""Testa uma lista de empresas nas plataformas de recrutamento e salva as que têm vagas.

Uso: python pesquisa/sondar_empresas.py <saida.json> nome1 nome2 ...
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import buscar_vagas as b  # noqa: E402

saida, nomes = Path(sys.argv[1]), sys.argv[2:]
with ThreadPoolExecutor(12) as ex:
    resultado = {k: v for k, v in ex.map(b.buscar_empresa, {n: [n] for n in nomes}.items()) if v}
saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(resultado), "empresas com vagas:", ", ".join(f"{k}({v['plataforma']}:{len(v['vagas'])})" for k, v in resultado.items()))
