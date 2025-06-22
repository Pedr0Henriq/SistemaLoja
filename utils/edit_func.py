
from flask import jsonify

from utils.parser import parse_mensagem
from utils.pdf_generator import gerar_pdf
from utils.saver import carregar_pedidos_json, salvar_pedido_json


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