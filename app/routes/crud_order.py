from datetime import datetime
import re
import traceback
import uuid
from flask import Blueprint, jsonify, redirect, render_template, render_template_string, request, url_for
from database.database import get_db
from utils.services import PedidoParsingException, excluir_anexos, parse_mensagem, validar_telefone


crud_bp = Blueprint('crud', __name__)


@crud_bp.route("/pedido/<string:pedido_id>/excluir", methods=["DELETE"])
def excluir_pedido(pedido_id):
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('SELECT cliente FROM pedidos WHERE id = ?', (pedido_id,))
        pedido = cursor.fetchone()
        if not pedido:
            return jsonify({"erro": "Pedido não encontrado."}), 404
        cursor.execute('SELECT path FROM foto_item WHERE pedido_id = ?', (pedido_id,))
        fotos = cursor.fetchall()
        fotos = [foto[0] for foto in fotos]
        excluir_anexos(fotos)
        cursor.execute('DELETE FROM pedidos WHERE id = ?', (pedido_id,))
        cursor.execute('DELETE FROM itens WHERE pedido_id = ?', (pedido_id,))
        cursor.execute('DELETE FROM foto_item WHERE pedido_id = ?', (pedido_id,))
        conn.commit()
        return redirect(url_for('employee.painel'))
    except Exception as e:
        print("Erro ao excluir pedido:", traceback.format_exc())
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        if conn:
            conn.close()


@crud_bp.route("/pedido/<string:pedido_id>/editar", methods=["GET"])
def view_editar_pedido(pedido_id):
    conn = None
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
    finally:
        if conn:
            conn.close()

@crud_bp.route("/pedido/<string:pedido_id>/editar", methods=["POST"])
def salver_editar_pedido(pedido_id):
    conn = None
    try:
        id = request.form.get('id')

        telefone = request.form.get('telefone')
        if not validar_telefone(telefone):
            return jsonify({'erro':'Formato de telefone inválido.'}), 400

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE pedidos SET telefone= ? WHERE id = ?',(telefone,id,))
        

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
            try:
                quantidade = item['quantidade'].replace(',', '.')
                cursor.execute('UPDATE itens SET item= ?, quantidade = ?, unidade = ? WHERE pedido_id = ?',(item['item'],quantidade,item['unidade'],id,))
            except KeyError as e:
                return jsonify({'erro': f'Campo {str(e)} não encontrado.'}), 400
            except Exception as e:
                return jsonify({'erro': f'Erro ao atualizar item: {str(e)}'}), 500
        conn.commit() 
        return redirect(url_for('employee.painel'))
    except Exception as e:
        print("Erro ao editar pedido:", traceback.format_exc())
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        if conn:
            conn.close()


@crud_bp.route("/pedido", methods=["POST"])
def receber_pedido():
    link = url_for('client.index')
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
        pedido = {
            'id': str(uuid.uuid4()),
            'cliente': data['cliente'].strip(),
            'telefone': data['telefone'].strip(),
            'data_hora': datetime.now().strftime("%d/%m/%Y %H:%M"),
            'status': 'pendente',
            'valor_total': '0.0'
        }
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pedidos VALUES (:id, :cliente, :telefone, :data_hora, :status, :valor_total)",
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
        return render_template_string(f"""
            <div style='padding: 20px;font-family: sans-serif;'>
              <h2>❌ Erro no pedido</h2>
                <p>{str(e)}</p>
                <p>Certifique-se de que a mensagem está no formato correto: <strong>quantidade + unidade (m/u/c) x nome do item</strong></p>
                <p>Exemplo: <code>2,5m x TNT preto</code></p>
              <a href="{link}">Tentar novamente</a>
            </div>
        """)
    except ValueError as e:
        return render_template_string(f"""
            <div style='padding: 20px;font-family: sans-serif;'>
              <h2>❌ Erro de validação: {str(e)}</h2>
              <a href="{link}">Tentar novamente</a>
            </div>
        """)

    except Exception as e:
        print(f"[ERRO INTERNO] {str(e)}",flush=True)

        return render_template_string(f"""
            <div style='padding: 20px; font-family: sans-serif;'>
            <h2>❌ Erro inesperado</h2>
            <p>Algo deu errado ao processar seu pedido.</p>
            <p>Por favor, tente novamente ou entre em contato com o suporte.</p>
            <a href="{link}">Tentar novamente</a>
            </div>
        """)