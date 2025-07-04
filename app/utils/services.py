from flask import jsonify
import re
import unicodedata
from utils.enum import Unidades
from utils.pdf_generator import gerar_pdf
import json



def edit_order(novos_dados):
    mensagem = novos_dados.get("mensagem")
    if not mensagem:
        return jsonify({"erro": "Mensagem do pedido não pode ser vazia."}), 400
    if not isinstance(mensagem, str):
        return jsonify({"erro": "Mensagem deve ser uma string."}), 400
    itens = parse_mensagem(mensagem)
    pedidos = carregar_pedidos_json()
    pedido_id = novos_dados.get("id")
    if not pedido_id:
        return jsonify({"erro": "ID do pedido não fornecido."}), 400
    pedido = [p for p in pedidos if p.get("id") == pedido_id]
    if not pedido:
        return jsonify({"erro": "Pedido não encontrado."}), 404
    pedido["itens"] = itens
    caminho_pdf = gerar_pdf(pedido_id, pedido["itens"], pedido["cliente"], telefone_cliente=pedido["telefone"])
    salvar_pedido_json(pedido_id, pedido["cliente"], pedido["itens"], pedido["telefone"])
    return jsonify({
            "mensagem": "Pedido editado com sucesso.",
            "pdf_path": caminho_pdf
    }),200


class PedidoParsingException(Exception):
    pass

def normalize_text(texto):
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')

def parse_mensagem(mensagem):
    try:        
        mensagem = mensagem.replace("\\n", "\n")
        linhas = mensagem.strip().splitlines()
        pedido = []
        
        for linha in linhas:
            match = re.match(r"^(\d+)([muc])\sx\s([a-zA-ZÀ-ÿ\s]+)$", linha, re.IGNORECASE)
            if match:
                qtd, unidade, item = match.groups()
                unidade = unidade.lower()
                if Unidades.is_valid(unidade):
                    pedido.append({
                        "item": item.strip(),
                        "quantidade": int(qtd),
                        "unidade": unidade
                    })
                else:
                    raise PedidoParsingException(f"Unidade inválida: {unidade}. Use as opções: m (metro), c (centímetro), u (unidade).")
        
        return pedido
    except Exception as e:
        raise PedidoParsingException("Falha ao interpretar o pedido.") from e
    
    
def validar_telefone(telefone):
    """Valida telefone no formato (XX) XXXX-XXXX ou (XX) XXXXX-XXXX"""
    padrao = re.compile(r'^\(\d{2}\) \d{4,5}-\d{4}$')
    return bool(padrao.match(telefone))