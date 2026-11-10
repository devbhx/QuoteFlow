"""Gera propostas locais; consulta o repositório sem alterar os dados salvos."""

from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from formatacao import formatar_moeda
from repositorio import buscar_orcamento, buscar_prestador


PASTA_EXPORTACOES = Path(__file__).resolve().parent / "exports"


def registrar_fontes():
    # Fontes distribuídas com a dependência, sem depender das fontes do computador.
    pasta = Path(reportlab.__file__).parent / "fonts"
    if "QuoteFlow" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("QuoteFlow", str(pasta / "Vera.ttf")))
        pdfmetrics.registerFont(TTFont("QuoteFlow-Bold", str(pasta / "VeraBd.ttf")))
        pdfmetrics.registerFontFamily("QuoteFlow", normal="QuoteFlow", bold="QuoteFlow-Bold")


def gerar_pdf(orcamento, prestador, exportado_em):
    """Monta o PDF em memória antes de criar qualquer arquivo de saída."""
    registrar_fontes()
    azul = colors.HexColor("#163A53")
    cinza = colors.HexColor("#53616C")
    corpo = ParagraphStyle("Corpo", fontName="QuoteFlow", fontSize=9, leading=14,
                           textColor=azul, spaceAfter=7, splitLongWords=True)
    titulo = ParagraphStyle("Titulo", parent=corpo, fontName="QuoteFlow-Bold", fontSize=22, leading=28)
    secao = ParagraphStyle("Secao", parent=corpo, fontName="QuoteFlow-Bold", fontSize=11,
                           spaceBefore=12, keepWithNext=True)
    celula = ParagraphStyle("Celula", parent=corpo, fontSize=8, leading=12, spaceAfter=0)
    numero = ParagraphStyle("Numero", parent=celula, alignment=TA_RIGHT, fontSize=7.5)
    total = ParagraphStyle("Total", parent=numero, fontName="QuoteFlow-Bold", fontSize=11, leading=15)
    cabecalho = ParagraphStyle("Cabecalho", parent=celula, textColor=colors.white, fontName="QuoteFlow-Bold")

    def paragrafo(texto, estilo=corpo):
        # Conteúdo digitado nunca vira marcação, link ou imagem do ReportLab.
        return Paragraph(escape(str(texto)).replace("\n", "<br/>"), estilo)

    def campo(rotulo, valor):
        return Paragraph(f"<b>{rotulo}:</b> {escape(str(valor)).replace(chr(10), '<br/>')}", corpo)

    numero_orcamento = orcamento["id"]
    criado_em = datetime.fromisoformat(orcamento["criado_em"]).astimezone()
    conteudo = [
        paragrafo("PROPOSTA COMERCIAL", titulo),
        paragrafo(f"Orçamento #{numero_orcamento} • {criado_em:%d/%m/%Y}", corpo),
        paragrafo("Prestador", secao),
        paragrafo(prestador["nome"]),
    ]
    if prestador["contato"]:
        conteudo.append(paragrafo(prestador["contato"]))
    conteudo.extend([paragrafo("Cliente e proposta", secao),
                     campo("Cliente", orcamento["cliente"])])
    if orcamento["validade"]:
        conteudo.append(campo("Válido até", date.fromisoformat(orcamento["validade"]).strftime("%d/%m/%Y")))
    conteudo.append(paragrafo("Serviços", secao))
    linhas = [[paragrafo(t, cabecalho) for t in ("Descrição", "Qtd.", "Preço unitário", "Subtotal")]]
    for item in orcamento["servicos"]:
        linhas.append([
            paragrafo(item["nome"], celula), paragrafo(item["quantidade"], numero),
            paragrafo(formatar_moeda(item["valor_unitario"]), numero),
            paragrafo(formatar_moeda(item["subtotal"]), numero),
        ])
    tabela = LongTable(linhas, colWidths=[84*mm, 18*mm, 36*mm, 36*mm],
                      repeatRows=1, splitInRow=1, hAlign="LEFT")
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), azul),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F4F7")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    conteudo.extend([tabela, Spacer(1, 6*mm)])
    resumo = Table([
        [paragrafo("Subtotal geral"), paragrafo(formatar_moeda(orcamento["subtotal_geral"]), numero)],
        [paragrafo(f"Desconto ({orcamento['percentual_desconto']}%)"),
         paragrafo(formatar_moeda(orcamento["valor_desconto"]), numero)],
        [paragrafo("TOTAL", secao), paragrafo(formatar_moeda(orcamento["total"]), total)],
    ], colWidths=[60*mm, 50*mm], hAlign="RIGHT")
    resumo.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                               ("LINEABOVE", (0, 2), (-1, 2), 1, azul)]))
    conteudo.append(resumo)
    for rotulo, chave in (("Condições de pagamento", "condicoes_pagamento"), ("Observações", "observacoes")):
        if orcamento[chave]:
            conteudo.extend([paragrafo(rotulo, secao), paragrafo(orcamento[chave])])

    def rodape(canvas, documento):
        canvas.saveState()
        canvas.setFont("QuoteFlow", 7)
        canvas.setFillColor(cinza)
        canvas.drawString(18*mm, 12*mm, f"Orçamento #{numero_orcamento} • Exportado em {exportado_em:%d/%m/%Y %H:%M %z}")
        canvas.drawRightString(A4[0] - 18*mm, 12*mm, f"Página {documento.page}")
        canvas.restoreState()

    arquivo = BytesIO()
    documento = SimpleDocTemplate(
        arquivo, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
        topMargin=18*mm, bottomMargin=22*mm,
        title=f"Orçamento #{numero_orcamento}", author=prestador["nome"],
    )
    documento.build(conteudo, onFirstPage=rodape, onLaterPages=rodape)
    return arquivo.getvalue()


def exportar_orcamento(conexao, identificador, pasta=PASTA_EXPORTACOES):
    """Exporta sem sobrescrever; None indica orçamento inexistente."""
    orcamento = buscar_orcamento(conexao, identificador)
    if orcamento is None:
        return None
    prestador = buscar_prestador(conexao)
    if prestador is None:
        raise ValueError("Configure o nome do prestador na opção 10 antes de exportar.")
    exportado_em = datetime.now().astimezone()
    dados = gerar_pdf(orcamento, prestador, exportado_em)
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    base = f"orcamento_{identificador}_{exportado_em:%Y%m%d_%H%M%S}"
    sufixo = 0
    while True:
        caminho = pasta / f"{base}{'_' + str(sufixo) if sufixo else ''}.pdf"
        try:
            arquivo = caminho.open("xb")
        except FileExistsError:
            sufixo += 1
            continue
        try:
            with arquivo:
                arquivo.write(dados)
        except OSError:
            # Remove somente o arquivo incompleto criado por esta tentativa.
            caminho.unlink(missing_ok=True)
            raise
        return caminho
