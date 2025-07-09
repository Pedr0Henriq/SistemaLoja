import traceback
from flask import Blueprint, json, jsonify, redirect, request, url_for

import requests

from database.database import get_db
from utils.services import excluir_anexos



route = 'http://evolutionapi:8080'

whatsapp_bp = Blueprint('whatsapp', __name__)


@whatsapp_bp.route("/pedido/<pedido_id>/whatsapp", methods=["POST"])
def enviar_whatsapp(pedido_id):
    conn = None
    try:
        cliente = request.form.get("cliente")
        telefone = request.form.get("telefone")
        valor = request.form.get("valor")
        itens_json = request.form.get("itens")
        if not cliente or not telefone or not valor or not itens_json:
            return jsonify({"erro": "Campos ausentes são obrigatórios."}), 400
        
        try:
            itens = json.loads(itens_json)
        except json.JSONDecodeError:
            return jsonify({"erro": "Formato de itens inválido."}), 400
        
        lista = "\n".join([f"- {item['quantidade']} {item['unidade']} x {item['item']}" for item in itens])

        telefone = ''.join(filter(str.isdigit, telefone))
        mensagem = (
            f"Olá {cliente}! Seu pedido:\n{lista}\n"
            f"Total: R$ {valor}\n\n"
            f"Está disponível pra retirada!\n"
            f"Lembrando que o pagamento é feito no local. E caso a opção de pagamento for cartão, haverá uma taxa no valor."            
        )

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE pedidos SET valor_total = ? WHERE id = ?", (valor, pedido_id))
        cursor.execute('UPDATE pedidos SET status = "aguardando retirada" WHERE id = ?', (pedido_id,))
        conn.commit()
        return evolution_api(telefone, mensagem)
    except Exception as e:
        print("Erro ao enviar WhatsApp:", traceback.format_exc(),flush=True)
        return jsonify({"erro": f"Erro interno no servidor. {e}"}), 500
    finally:
        if conn:
            conn.close()


@whatsapp_bp.route("/pedido/<pedido_id>/concluir", methods=["POST"])
def marcar_entregue(pedido_id):
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE pedidos SET status = 'entregue' WHERE id = ?", (pedido_id,))
        conn.commit()
        return redirect(url_for("employee.painel"))
    except Exception as e:
        return f"Erro ao marcar como entregue: {str(e)}", 500
    finally:
        if conn:
            conn.close()


@whatsapp_bp.route("/pedido/<pedido_id>/cancelar", methods=["POST"])
def cancelar_pedido(pedido_id):
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT cliente, telefone FROM pedidos WHERE id = ?", (pedido_id,))
        pedido = cursor.fetchone()
        if not pedido:
            return jsonify({"erro": "Pedido não encontrado"}), 404
        cursor.execute('SELECT path FROM foto_item WHERE pedido_id = ?', (pedido_id,))
        fotos = cursor.fetchall()
        fotos = [foto[0] for foto in fotos]
        cliente, telefone = pedido
        telefone = ''.join(filter(str.isdigit, telefone))
        mensagem = (
            f"Olá {cliente}, seu pedido foi cancelado.\n"
            "Se tiver dúvidas, entre em contato conosco."
        )
        excluir_anexos(fotos)
        cursor.execute('DELETE FROM pedidos WHERE id = ?', (pedido_id,))
        cursor.execute('DELETE FROM itens WHERE pedido_id = ?', (pedido_id,))
        cursor.execute('DELETE FROM foto_item WHERE pedido_id = ?', (pedido_id,))
        conn.commit()
        return evolution_api(telefone, mensagem)
    except Exception as e:
        print("Erro ao cancelar pedido:", traceback.format_exc(),flush=True)
        return jsonify({"erro": f"Erro interno no servidor. {e}"}), 500
    finally:
        if conn:
            conn.close()


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
        else:
            print(f"Erro ao enviar mensagem via Evolution API: {response.text}",flush=True)
            return jsonify({
                "erro": "Erro ao enviar mensagem via Evolution API.",
                "status_code": response.status_code,
                "detalhes": response.text
            }), 502
    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão com a Evolution API: {e}",flush=True)
        return jsonify({
            "erro": f"Erro de conexão com a Evolution API: {e}",
            "detalhes": str(e),}), 503