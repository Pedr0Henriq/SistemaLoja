# pdf_generator.py
from fpdf import FPDF
import os
from datetime import datetime

class PDFGenerationException(Exception):
    pass

def gerar_pdf(id,pedido, nome_cliente="Cliente", caminho_saida="static/pedidos",telefone_cliente=""):
    try:
        os.makedirs(caminho_saida, exist_ok=True)
        data_hoje = datetime.now().strftime("%d/%m/%Y")

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Fonte título
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "ARMARINHO GLÓRIA", ln=True, align="L")

        pdf.set_font("Arial", size=10)
        pdf.cell(0, 5, "Júlio Veloso, 142", ln=True)
        pdf.cell(0, 5, "Fone: (81) 99238-9452", ln=True)
        pdf.cell(0, 5, "Aceitamos todos os cartões", ln=True)
        pdf.ln(10)

        # Informações do cliente
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, f"Nome: {nome_cliente}", ln=True)
        if telefone_cliente:
            pdf.cell(0, 10, f"Telefone: {telefone_cliente}", ln=True)
        else:
            pdf.cell(0, 10, "Telefone: Não informado", ln=True)
        pdf.cell(0, 10, f"Data: {data_hoje}", ln=True)
        pdf.cell(0,10,f"Pedido: {id}", ln=True)
        pdf.ln(5)

        # Tabela de itens
        pdf.set_font("Arial", "B", 11)
        pdf.cell(20, 10, "Qnt.", 1, 0, "C")
        pdf.cell(90, 10, "Descrição do Produto/Serviço", 1, 0, "C")
        pdf.cell(40, 10, "Valor Unit.", 1, 0, "C")
        pdf.cell(40, 10, "TOTAL", 1, 1, "C")

        pdf.set_font("Arial", size=11)
        for item in pedido:
            qtd = str(item.get("quantidade", ""))
            nome = item.get("item", "")
            valor_unit = item.get("valor", "-")
            total = "-"

            if isinstance(valor_unit, (int, float)):
                total_calc = item["quantidade"] * valor_unit
                valor_unit = f"R$ {valor_unit:.2f}"
                total = f"R$ {total_calc:.2f}"

            pdf.cell(20, 10, qtd, 1, 0, "C")
            pdf.cell(90, 10, nome, 1, 0)
            pdf.cell(40, 10, valor_unit, 1, 0, "C")
            pdf.cell(40, 10, total, 1, 1, "C")

        nome_arquivo = f"{nome_cliente.replace(' ', '_').lower()}_pedido{id}.pdf"
        caminho_completo = os.path.join(caminho_saida, nome_arquivo)
        pdf.output(caminho_completo)
        return caminho_completo

    except Exception as e:
        raise PDFGenerationException("Não foi possível gerar o PDF.") from e
