from datetime import datetime
import os
import pickle
import sqlite3
import traceback
from flask import Blueprint, g, json, jsonify, render_template, request

from database import get_db
from utils.services import validar_telefone


employee_bp = Blueprint('employee', __name__)

@employee_bp.route("/painel")
def painel():
    status = request.args.getlist("status")
    try:
        if not status:
            status = ["pendente", "entregue", "aguardando pagamento", "aguardando retirada"]
        placeholders = ','.join('?' for _ in status)
        conn = get_db()
        conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT id FROM pedidos WHERE status IN ({placeholders})", status)
        order_ids = cursor.fetchall()
        
        pedidos = []
        
        for row in order_ids:
            order_id = row[0]
            
            cursor.execute("""
                SELECT 
                    p.id, p.cliente, p.telefone, p.data_hora, p.status, p.arquivo_pdf,
                    i.id as item_id, i.item, i.quantidade, i.unidade,
                    f.path as foto_path
                FROM pedidos p
                LEFT JOIN itens i ON p.id = i.pedido_id
                LEFT JOIN foto_item f ON p.id = f.pedido_id AND i.id = f.item_id
                WHERE p.id = ?
                ORDER BY i.id
            """, (order_id,))
            
            items_data = cursor.fetchall()
            
            itens_fotos = []
            
            for row in items_data:

                if not pedidos or pedidos[-1]['id'] != order_id:
                    pedidos.append({
                        "id": row[0],
                        "cliente": row[1],
                        "telefone": row[2],
                        "data_hora": row[3],
                        "status": row[4],
                        "arquivo_pdf": row[5],
                        "itens": []
                    })
                

                if row[6]:  
                    if not itens_fotos or itens_fotos[-1]['item_id'] != row[6]:
                        itens_fotos.append({
                            "item_id": row[6],
                            "item": row[7],
                            "quantidade": row[8],
                            "unidade": row[9],
                            "fotos": []
                        })
                    

                    if row[10]:  
                        itens_fotos[-1]['fotos'].append(row[10])
            

            if pedidos and pedidos[-1]['id'] == order_id:
                pedidos[-1]['itens'] = itens_fotos
        
        conn.close()
        print("Pedidos carregados:", pedidos)
        return render_template("funcionario/view.html", pedidos = pedidos)
    except sqlite3.Error as e:
        print("Erro ao acessar o banco de dados:", e)
        return jsonify({"erro": "Erro ao acessar o banco de dados."}), 500
    


@employee_bp.route("/pedido/<pedido_id>/confirmar", methods=["GET"])
def confirmar_envio(pedido_id):
    try:
        cliente = request.args.get("cliente")
        telefone = request.args.get("telefone")
        itens = json.loads(request.args.get("itens"))
        
        if not validar_telefone(telefone):
            return jsonify({"erro": "Telefone inválido."}), 400
        
        return render_template("funcionario/confirmar_envio.html", 
                           pedido_id=pedido_id, 
                           cliente=cliente, 
                           telefone=telefone, 
                           itens=itens)
    
    except Exception as e:
        print("Erro ao confirmar envio:", traceback.format_exc())
        return jsonify({"erro": "Erro interno no servidor."}), 500
    



def get_ultimo_pedido():
    if not hasattr(g, 'ultimo_pedido'):
        # Tenta carregar de arquivo
        if os.path.exists('ultimo_pedido.pkl'):
            with open('ultimo_pedido.pkl', 'rb') as f:
                g.ultimo_pedido = pickle.load(f)
        else:
            g.ultimo_pedido = None
    return g.ultimo_pedido

def set_ultimo_pedido(valor):
    g.ultimo_pedido = valor
    # Persiste em arquivo
    with open('ultimo_pedido.pkl', 'wb') as f:
        pickle.dump(valor, f)

@employee_bp.route("/verificar_novos_pedidos")
def verificar_novos_pedidos():
    try:
    # Verifica se há novos pedidos
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT data_hora FROM pedidos ORDER BY data_hora DESC LIMIT 1")
        ultimo_pedido = cursor.fetchone()
        conn.close()
        if ultimo_pedido is None:
            return jsonify({"novo": False})
        ultimo_pedido = datetime.strptime(ultimo_pedido[0], "%d/%m/%Y %H:%M")

        ultimo = get_ultimo_pedido()
        
        if ultimo is None:
            set_ultimo_pedido(ultimo_pedido)
            return jsonify({"novo": False})
            
        if ultimo_pedido > ultimo:
            set_ultimo_pedido(ultimo_pedido)
            return jsonify({"novo": True})
            
        return jsonify({"novo": False})

    except Exception as e:
        print("Erro ao verificar novos pedidos:", traceback.format_exc())
        return jsonify({"erro": str(e)}), 500