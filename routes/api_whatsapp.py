import traceback
from flask import Blueprint, json, jsonify, redirect, request, url_for
from urllib.parse import quote

import requests

from database import get_db
from utils.services import validar_telefone


whatsapp_bp = Blueprint('whatsapp', __name__)

@whatsapp_bp.route("/pedido/<pedido_id>/whatsapp", methods=["POST"])
def enviar_whatsapp(pedido_id):
    try:
        cliente = request.form.get("cliente")
        telefone = request.form.get("telefone")
        valor = request.form.get("valor")
        itens = json.loads(request.form.get("itens"))

        lista = "\n".join([f"- {item['quantidade']} x {item['item']}" for item in itens])

        telefone = ''.join(filter(str.isdigit, telefone))
        mensagem = (
            f"Olá {cliente}! Seu pedido:\n{lista}\n"
            f"Total: R$ {valor}\n\n"
            "Escolha a forma de pagamento:\n"
            "1️⃣ Pix: 037.886.844-61\n"
            "Pague na retirada\n"
            "2️⃣ Dinheiro\n"
            "3️⃣ Cartão\n"
        )
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE pedidos SET status = "aguardando pagamento" WHERE id = ?', (pedido_id,))
        conn.commit()
        conn.close()
        return open_whatsapp_link(telefone, mensagem)
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
        return open_whatsapp_link(telefone, mensagem)
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

@whatsapp_bp.route("/pedido/<pedido_id>/enviar_pagamento", methods=["POST"])
def enviar_pagamento(pedido_id):
    try:
        telefone = request.form.get("telefone")
        if not validar_telefone(telefone):
            return jsonify({"erro": "Telefone inválido."}), 400
        telefone = ''.join(filter(str.isdigit, telefone))
        tipo_pagamento = request.form.get("tipo")
        if tipo_pagamento == 'pix':
            mensagem = (
                f"Olá! Nosso Pix é: 037.886.844-61\n"
                "Por favor, envie o comprovante de pagamento para confirmar seu pedido.\n"
                "Agradecemos pela preferência!"
            )
            link = f"https://wa.me/55{telefone}?text={quote(mensagem)}"
            return open_whatsapp_link(telefone, mensagem)
        else:    
            response = requests.post(
                f"http://localhost:5000/pedido/{pedido_id}/retirada"
            )
            if response.ok:
                return redirect(url_for("employee.painel"))
            else:
                return jsonify({"erro": "Erro ao marcar pedido como pronto para retirada."}), 500
    except Exception as e:
        print("Erro ao enviar confirmação de pagamento:", traceback.format_exc())
        return jsonify({"erro": f"Erro interno no servidor. {e}"}), 500
    


def open_whatsapp_link(telefone, mensagem):
    telefone = ''.join(filter(str.isdigit, telefone))
    link = f"https://wa.me/55{telefone}?text={quote(mensagem)}"
    return f"""
            <script>
                window.open('{link}', '_blank');
                window.history.back();  // Volta para a página anterior
            </script>
        """