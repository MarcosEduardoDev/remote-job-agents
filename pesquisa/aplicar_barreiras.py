"""Aplica as barreiras da triagem a uma vaga lida no navegador e atualiza a fila (usado pelo agente leitor).

Uso: python pesquisa/aplicar_barreiras.py <id da fila> <arquivo .txt com o texto da vaga> [destino]
- destino (opcional): link real de candidatura achado na página (ex.: o "Apply" do Himalayas).
O texto fica salvo em fila/textos/<id>.txt para o redator e o verificador.
"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fila as F  # noqa: E402
from categorias import categorizar  # noqa: E402
from filtrar_vagas import tipo_contrato  # noqa: E402
from triagem_detalhada import BARREIRAS, SO_AVISO  # noqa: E402

TEXTOS = F.RAIZ / "fila" / "textos"


def main():
    i, arq = sys.argv[1], Path(sys.argv[2])
    destino = sys.argv[3] if len(sys.argv) > 3 else None
    corpo = " ".join(arq.read_text(encoding="utf-8").replace("\\n", " ").split())
    with F.trava():
        _aplicar(i, arq, destino, corpo)


def _aplicar(i, arq, destino, corpo):
    fila = F.carregar()
    e = fila[i]
    barreiras, avisos = [], []
    for nome, padrao in BARREIRAS.items():
        m = padrao.search(corpo)
        if m:
            trecho = f"{nome}: '{corpo[max(0, m.start() - 40):m.end() + 40]}'"
            (avisos if nome in SO_AVISO else barreiras).append(trecho)
    e.update(barreiras=barreiras, avisos=avisos, erro="", contrato=tipo_contrato(f"{e.get('titulo', '')} {corpo}"),
             categoria=categorizar(e.get("titulo", ""), corpo, None))
    if destino:
        e["destino"] = destino
    TEXTOS.mkdir(parents=True, exist_ok=True)
    shutil.copy(arq, TEXTOS / f"{i}.txt")
    if barreiras:
        F.mudar(fila, i, "barrada", "leitor: " + "; ".join(b.split(":")[0] for b in barreiras))
    else:
        status, nota = F.rota(e)
        if status == "ler_no_navegador":  # o leitor não achou o site final: vai para a fila manual
            status, nota = "manual", "fila manual (site final não encontrado pelo leitor; prioridade Baixa)"
            e["prioridade_manual"], e["motivo_manual"] = "Baixa", "site final não encontrado"
        F.mudar(fila, i, status, "leitor: " + nota + (" (aviso de idioma)" if avisos else ""))
    F.salvar(fila)
    print(f"{i} -> {e['status']} | {e['contrato']} | barreiras: {[b.split(':')[0] for b in barreiras]} | avisos: {len(avisos)}")


if __name__ == "__main__":
    main()
