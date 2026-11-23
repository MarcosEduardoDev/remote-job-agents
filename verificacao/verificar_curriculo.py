"""Confere se um currículo gerado é igual ao mestre do mesmo idioma, exceto pelo subtítulo.

Uso: python verificacao/verificar_curriculo.py <pdf gerado> <pt|en|fr>
Saída: OK ou a lista de diferenças. Código de saída 0 = OK, 1 = problema.
"""

import sys
from pathlib import Path

from pypdf import PdfReader

RAIZ = Path(__file__).resolve().parent.parent


def linhas(pdf: Path) -> list[str]:
    leitor = PdfReader(str(pdf))
    texto = "\n".join(p.extract_text() for p in leitor.pages)
    return [l.strip() for l in texto.splitlines() if l.strip()], len(leitor.pages)


def main() -> int:
    gerado, idioma = Path(sys.argv[1]), sys.argv[2]
    mestre = RAIZ / "curriculos" / "mestres" / f"curriculo-{idioma}.pdf"
    a, paginas_a = linhas(mestre)
    b, paginas_b = linhas(gerado)
    problemas = []
    if paginas_b != 1:
        problemas.append(f"o currículo gerado tem {paginas_b} páginas (deve ter 1)")
    # Linha 0 = nome, linha 1 = subtítulo (pode mudar). Todo o resto deve ser idêntico.
    if a[0] != b[0]:
        problemas.append(f"nome diferente: {b[0]!r}")
    resto_a, resto_b = a[2:], b[2:]
    if resto_a != resto_b:
        for i, (x, y) in enumerate(zip(resto_a, resto_b)):
            if x != y:
                problemas.append(f"linha {i + 3} difere do mestre: {y!r} (mestre: {x!r})")
                break
        if len(resto_a) != len(resto_b):
            problemas.append(f"número de linhas diferente ({len(resto_b)} contra {len(resto_a)} no mestre)")
    print(f"subtítulo: {b[1]!r}")
    if problemas:
        print("PROBLEMA:\n- " + "\n- ".join(problemas))
        return 1
    print("OK: idêntico ao mestre exceto pelo subtítulo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
