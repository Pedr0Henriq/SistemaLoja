from datetime import datetime
import re
import traceback
import uuid
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from database.database import get_db
from utils.pdf_generator import PDFGenerationException, gerar_pdf
from utils.services import PedidoParsingException, parse_mensagem, validar_telefone


crud_bp = Blueprint('crud', __name__)


@crud_bp.route("/pedido/<string:pedido_id>/excluir", methods=["DELETE"])
def excluir_pedido(pedido_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM pedidos WHERE id = ?', (pedido_id,))
        cursor.execute('DELETE FROM itens WHERE pedido_id = ?', (pedido_id,))
        cursor.execute('DELETE FROM foto_item WHERE pedido_id = ?', (pedido_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('employee.painel'))
    except Exception as e:
        print("Erro ao excluir pedido:", traceback.format_exc())
        return jsonify({"erro": "Erro interno no servidor."}), 500


@crud_bp.route("/pedido/<string:pedido_id>/editar", methods=["GET"])
def view_editar_pedido(pedido_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM pedidos WHERE id = ?', (pedido_id,))
        pedido = cursor.fetchone()
        cursor.execute('SELECT * FROM itens WHERE pedido_id = ?',(pedido_id,))
        itens = cursor.fetchall()
        if not pedido:
            return jsonify({"erro": "Pedido não encontrado."}), 404
        return render_template("funcionario/edit_order.html", pedido = pedido, itens = itens)
    except Exception as e:
        print("Erro ao editar pedido:", traceback.format_exc())
        return jsonify({"erro": "Erro interno no servidor."}), 500

@crud_bp.route("/pedido/<string:pedido_id>/editar", methods=["POST"])
def salver_editar_pedido(pedido_id):
    try:
        id = request.form.get('id')

        telefone = request.form.get('telefone')
        if not validar_telefone(telefone):
            return jsonify({'erro':'Formato de telefone inválido.'}), 400
        
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE pedidos SET telefone= ?, data_hora = ? WHERE id = ?',(telefone,data_hora,id,))
        

        itens = []
        for key, value in request.form.items():
            match = re.match(r"itens\[(\d+)\]\[(\w+)\]", key)
            if match:
                index, campo = match.groups()
                index = int(index)
                while len(itens) <= index:
                    itens.append({})
                itens[index][campo] = value
        for item in itens:
            cursor.execute('UPDATE itens SET item= ?, quantidade = ?, unidade = ? WHERE pedido_id = ?',(item['item'],item['quantidade'],item['unidade'],id,))
        conn.commit() 
        conn.close()
        return redirect(url_for('employee.painel'))
    except Exception as e:
        print("Erro ao editar pedido:", traceback.format_exc())
        return jsonify({"erro": "Erro interno no servidor."}), 500


@crud_bp.route("/pedido", methods=["POST"])
def receber_pedido():
    try:
        data = request.json

        if not all(key in data for key in ['cliente', 'mensagem', 'telefone']):
            return jsonify({"erro": "Dados incompletos. Certifique-se de enviar 'cliente', 'mensagem' e 'telefone'."}), 400
        if not data['cliente'].strip():
            return jsonify({"erro": "O nome do cliente não pode ser vazio."}), 400
        if not validar_telefone(data['telefone']):
            return jsonify({"erro": "Telefone inválido. Use o formato (XX) XXXXX-XXXX."}), 400

        mensagem = data['mensagem'].strip()
        mensagem = parse_mensagem(mensagem)
        fotos = data.get('fotos', [])
        print("Fotos recebidas:", fotos)
        pedido = {
            'id': str(uuid.uuid4()),
            'cliente': data['cliente'].strip(),
            'telefone': data['telefone'].strip(),
            'data_hora': datetime.now().strftime("%d/%m/%Y %H:%M"),
            'status': 'pendente',
            'valor_total': '0.0'
        }
        caminho_pdf = gerar_pdf(pedido,mensagem)
        pedido['arquivo_pdf'] = caminho_pdf
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pedidos VALUES (:id, :cliente, :telefone, :data_hora, :status, :arquivo_pdf, :valor_total)",
            pedido
        )
        for idx, item in enumerate(mensagem):
            cursor.execute("INSERT INTO itens (pedido_id, item, quantidade, unidade) VALUES (?, ?, ?, ?)",
            (pedido["id"],item['item'],item['quantidade'],item['unidade']))
            item_id = cursor.lastrowid
            if idx < len(fotos):
              caminho_foto = fotos[idx]
              cursor.execute("INSERT INTO foto_item (path, pedido_id, item_id) VALUES (?, ?, ?)",(caminho_foto, pedido['id'], item_id))
                           
        conn.commit()
        conn.close()
        return jsonify({
            "sucesso": True,
            "mensagem": "Pedido recebido com sucesso.",
            "pedido_id": pedido['id']
        }), 201
    except PedidoParsingException as e:
        return jsonify({"erro": str(e)}), 422

    except PDFGenerationException as e:
        return jsonify({"erro": "Erro ao gerar PDF: " + str(e)}), 500

    except ValueError as e:
        return jsonify({"erro": str(e)}), 400

    except Exception as e:
        print("Erro inesperado:", traceback.format_exc())
        return jsonify({"erro": "Erro interno no servidor."}), 500