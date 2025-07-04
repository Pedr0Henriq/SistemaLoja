import traceback
from flask import Blueprint, session, json, jsonify, redirect, render_template, request, url_for
from urllib.parse import quote

import requests

from database import get_db
from utils.services import validar_telefone


EVOLUTION_API_KEY = 'lipf0a8hf9srlm6f171bgb'
route = 'http://evolutionapi:8080'

whatsapp_bp = Blueprint('whatsapp', __name__)


@whatsapp_bp.route("/pedido/<pedido_id>/whatsapp", methods=["POST"])
def enviar_whatsapp(pedido_id):
    try:
        cliente = request.form.get("cliente")
        telefone = request.form.get("telefone")
        valor = request.form.get("valor")
        itens = json.loads(request.form.get("itens"))

        lista = "\n".join([f"- {item['quantidade']} x {item['item']}" for item in itens])

        link_pagamento = f"http://localhost:5000/pedido/{pedido_id}/enviar_pagamento"

        telefone = ''.join(filter(str.isdigit, telefone))
        mensagem = (
            f"Olá {cliente}! Seu pedido:\n{lista}\n"
            f"Total: R$ {valor}\n\n"
            f"Clique nesse link para escolher a forma de pagamento:\n{link_pagamento}"
            
        )
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE pedidos SET status = "aguardando pagamento" WHERE id = ?', (pedido_id,))
        conn.commit()
        conn.close()
        return evolution_api(telefone, mensagem)
    except Exception as e:
        print("Erro ao enviar WhatsApp:", traceback.format_exc())
        return jsonify({"erro": f"Erro interno no servidor. {e}"}), 500


@whatsapp_bp.route("/pedido/<pedido_id>/retirada", methods=["POST"])
def marcar_retirada(pedido_id):
    try:
        conn = get_db()
        conn.execute("UPDATE pedidos SET status = 'aguardando retirada' WHERE id = ?", (pedido_id,))
        conn.commit()
        cursor = conn.execute("SELECT cliente, telefone FROM pedidos WHERE id = ?", (pedido_id,))
        cliente, telefone = cursor.fetchone()
        conn.close()
        telefone = ''.join(filter(str.isdigit, telefone))
        mensagem = (
                f"Olá {cliente}! Seu pedido está pronto pra retirada!\n"
            )
        return evolution_api(telefone, mensagem)
    except Exception as e:
        print("Erro ao marcar retirada:", traceback.format_exc())
        return jsonify({"erro": f"Erro interno no servidor. {e}"}), 500


@whatsapp_bp.route("/pedido/<pedido_id>/concluir", methods=["POST"])
def marcar_entregue(pedido_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE pedidos SET status = 'entregue' WHERE id = ?", (pedido_id,))
        conn.commit()
        conn.close()
        return redirect(url_for("employee.painel"))
    except Exception as e:
        return f"Erro ao marcar como entregue: {str(e)}", 500

@whatsapp_bp.route("/pedido/<pedido_id>/enviar_pagamento", methods=["GET"])
def enviar_pagamento(pedido_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT cliente, telefone FROM pedidos WHERE id = ?", (pedido_id,))
        resultado = cursor.fetchone()
        cursor.execute('SELECT item, quantidade FROM itens WHERE pedido_id = ?', (pedido_id,))
        itens = cursor.fetchall()
        conn.close()
        return render_template("payment.html", cliente=resultado[0], telefone=resultado[1], itens=itens)
    except Exception as e:
        print("Erro ao enviar confirmação de pagamento:", traceback.format_exc())
        return jsonify({"erro": f"Erro interno no servidor. {e}"}), 500
    


def evolution_api(telefone, mensagem):
    telefone = ''.join(filter(str.isdigit, telefone))
    instance = 'Pedro'
    url = f"{route}/message/sendText/{instance}"
    headers = {
        "apikey": 'livia0416',
        "Content-Type": "application/json"
    }
    payload = {
    "number": f"55{telefone}",
    "textMessage": {"text": mensagem}
}

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.ok:
            return redirect(url_for("employee.painel"))
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar mensagem via Evolution API: {e}")
        return jsonify({"erro": "Erro ao enviar mensagem via Evolution API."}), 500