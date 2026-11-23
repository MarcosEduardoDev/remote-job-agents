"""Gera o currículo em PDF a partir do conteúdo mestre de um idioma.

Regra de ouro: o conteúdo mestre nunca é alterado por candidatura.
A única coisa que pode mudar por vaga é o subtítulo (--subtitulo).

Exemplos:
    python curriculos/gerar_curriculo.py --idioma pt
    python curriculos/gerar_curriculo.py --idioma en --subtitulo "Customer Support · Portuguese, English & French" --saida saida/zapier.pdf
"""

import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

PASTA = Path(__file__).resolve().parent
PASTA_CONTEUDO = PASTA / "conteudo"
PASTA_MESTRES = PASTA / "mestres"
IDIOMAS = ("pt", "en", "fr")

AZUL = HexColor("#1F3A5F")
TEXTO = HexColor("#222222")
CINZA = HexColor("#555555")
LINHA = HexColor("#C9D3E0")

ESTILOS = {
    "nome": ParagraphStyle("nome", fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=AZUL),
    "subtitulo": ParagraphStyle("subtitulo", fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=TEXTO),
    "contato": ParagraphStyle("contato", fontName="Helvetica", fontSize=9.5, leading=13, textColor=CINZA),
    "secao": ParagraphStyle("secao", fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=AZUL, spaceBefore=9),
    "cabecalho": ParagraphStyle("cabecalho", fontName="Helvetica-Bold", fontSize=9.5, leading=12.5, textColor=TEXTO, spaceBefore=3, spaceAfter=1),
    "texto": ParagraphStyle("texto", fontName="Helvetica", fontSize=9.5, leading=12.5, textColor=TEXTO),
}


def carregar_conteudo(idioma: str) -> dict:
    with open(PASTA_CONTEUDO / f"{idioma}.json", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def lista(itens: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(item, ESTILOS["texto"]), leftIndent=12) for item in itens],
        bulletType="bullet",
        start="•",
        bulletFontName="Helvetica",
        bulletFontSize=9.5,
        leftIndent=12,
        spaceBefore=1,
    )


def montar(conteudo: dict, subtitulo: str) -> list:
    link = f'<font color="{CINZA.hexval()}">%s</font>'
    contato = "  |  ".join([
        f'<a href="mailto:{conteudo["email"]}">{link % conteudo["email"]}</a>',
        f'<a href="{conteudo["linkedin"]}">{link % "LinkedIn"}</a>',
        f'<a href="{conteudo["github"]}">{link % "GitHub"}</a>',
    ])

    elementos = [
        Paragraph(conteudo["nome"], ESTILOS["nome"]),
        Paragraph(escape(subtitulo), ESTILOS["subtitulo"]),
        Paragraph(conteudo["localizacao"], ESTILOS["contato"]),
        Paragraph(contato, ESTILOS["contato"]),
        Spacer(1, 4),
    ]

    for secao in conteudo["secoes"]:
        titulo = [
            Paragraph(secao["titulo"], ESTILOS["secao"]),
            HRFlowable(width="100%", thickness=0.6, color=LINHA, spaceBefore=2, spaceAfter=4),
        ]
        corpo = []
        if "texto" in secao:
            corpo.append(Paragraph(secao["texto"], ESTILOS["texto"]))
        if "itens" in secao:
            corpo.append(lista(secao["itens"]))
        for bloco in secao.get("blocos", []):
            corpo.append(Paragraph(bloco["cabecalho"], ESTILOS["cabecalho"]))
            corpo.append(lista(bloco["itens"]))
        # Título nunca fica sozinho no pé da página.
        elementos.append(KeepTogether(titulo + corpo[:2]))
        elementos.extend(corpo[2:])

    return elementos


def gerar(idioma: str, subtitulo: str | None = None, saida: Path | None = None) -> Path:
    conteudo = carregar_conteudo(idioma)
    subtitulo = subtitulo or conteudo["subtitulo"]
    saida = saida or PASTA_MESTRES / f"curriculo-{idioma}.pdf"
    saida.parent.mkdir(parents=True, exist_ok=True)

    documento = SimpleDocTemplate(
        str(saida),
        pagesize=A4,
        leftMargin=1.9 * cm,
        rightMargin=1.9 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title=f"{conteudo['nome'].title()} - {subtitulo}",
        author=conteudo["nome"].title(),
    )
    documento.build(montar(conteudo, subtitulo))
    return saida


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera o currículo em PDF.")
    parser.add_argument("--idioma", choices=IDIOMAS, help="pt, en ou fr (sem isso, gera os três mestres)")
    parser.add_argument("--subtitulo", help="subtítulo adaptado à vaga (padrão: o do conteúdo mestre)")
    parser.add_argument("--saida", type=Path, help="caminho do PDF gerado")
    args = parser.parse_args()

    if args.idioma is None:
        if args.subtitulo or args.saida:
            parser.error("--subtitulo e --saida exigem --idioma")
        for idioma in IDIOMAS:
            print(gerar(idioma))
    else:
        print(gerar(args.idioma, args.subtitulo, args.saida))


if __name__ == "__main__":
    main()
