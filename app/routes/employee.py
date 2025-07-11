from datetime import datetime
import os
import pickle
import sqlite3
import traceback
from flask import Blueprint, g, json, jsonify, render_template, request

from database.database import get_db
from utils.services import validar_telefone


employee_bp = Blueprint('employee', __name__)

@employee_bp.route("/painel")
def painel():
    conn = None
    try:
        status = request.args.get("status")
        data_min = request.args.get("data_min")
        data_max = request.args.get("data_max")

        filtros = []
        parametros = []
        if status:
            filtros.append("p.status = ?")
            parametros.append(status)
        
        if data_min:
            filtros.append("strftime('%Y-%m-%d', p.data_hora) >= ?")
            parametros.append(data_min)
        if data_max:
            filtros.append("strftime('%Y-%m-%d', p.data_hora) <= ?")
            parametros.append(data_max)
        
        where_clause = "WHERE " + " AND ".join(filtros) if filtros else ""

        conn = get_db()
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT DISTINCT p.id FROM pedidos p {where_clause} ORDER BY p.data_hora DESC", parametros)
        order_ids = cursor.fetchall()
        
        pedidos = []
        
        for row in order_ids:
            order_id = row[0]
            
            cursor.execute("""
                SELECT 
                    p.id, p.cliente, p.telefone, p.data_hora, p.status,
                    i.id as item_id, i.item, i.quantidade, i.unidade,
                    f.path as foto_path
                FROM pedidos p
                LEFT JOIN itens i ON p.id = i.pedido_id
                LEFT JOIN foto_item f ON p.id = f.pedido_id AND i.id = f.item_id
                WHERE p.id = ?
                ORDER BY i.id
            """, (order_id,))
            
            items_data = cursor.fetchall()
            current_pedido = None
            current_item = None
            itens_fotos = []
            
            for row in items_data:

                if current_pedido is None:
                    current_pedido = {
                         "id": row["id"],
                    "cliente": row["cliente"],
                    "telefone": row["telefone"],
                    "data_hora": row["data_hora"],
                    "status": row["status"],
                    "itens": [] # Será preenchido no final
                    }
                
                item_id = row["item_id"]

                if current_item is None or current_item['item_id'] != item_id:
                    if current_item:
                        itens_fotos.append(current_item)
                    current_item = {
                        "item_id": item_id,
                        "item": row["item"],
                        "quantidade": row["quantidade"],
                        "unidade": row["unidade"],
                        "fotos": []
                    }
                foto_path = row["foto_path"]
                if foto_path:
                    current_item['fotos'].append(foto_path)
            if current_item:
                itens_fotos.append(current_item)
                
            if current_pedido:
                print(f"[PANEL] Pedido {current_pedido} carregado com {len(itens_fotos)} itens e fotos.", flush=True)
                current_pedido['itens'] = itens_fotos
                pedidos.append(current_pedido)
            
        print(f"[PANEL] Pedidos carregados: {pedidos}", flush=True)
        return render_template("funcionario/view.html", pedidos = pedidos)
    except sqlite3.Error as e:
        print("Erro ao acessar o banco de dados:", e, flush=True)
        return jsonify({"erro": f"Erro ao acessar o banco de dados. {e}"}), 500
    except Exception as e:
        print("Erro ao carregar o painel:", traceback.format_exc(), flush=True)
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        if conn:
            conn.close()
    


@employee_bp.route("/pedido/<pedido_id>/confirmar", methods=["GET"])
def confirmar_envio(pedido_id):
    try:
        cliente = request.args.get("cliente")
        telefone = request.args.get("telefone")
        itens_json = request.args.get("itens")
        

        if not cliente or not telefone or not itens_json:
            return jsonify({"erro": "Parâmetros ausentes."}), 400
        
        if not validar_telefone(telefone):
            return jsonify({"erro": "Telefone inválido."}), 400
        try:
            itens = json.loads(itens_json)
        except json.JSONDecodeError:
            return jsonify({"erro": "Formato de itens inválido."}), 400
        
        return render_template("funcionario/confirmar_envio.html", 
                           pedido_id=pedido_id, 
                           cliente=cliente, 
                           telefone=telefone, 
                           itens=itens)
    
    except Exception as e:
        print("Erro ao confirmar envio:", traceback.format_exc(), flush=True)
        return jsonify({"erro": "Erro interno no servidor."}), 500
    



def get_ultimo_pedido():
    if not hasattr(g, 'ultimo_pedido'):
        if os.path.exists('ultimo_pedido.pkl'):
            with open('ultimo_pedido.pkl', 'rb') as f:
                g.ultimo_pedido = pickle.load(f)
        else:
            g.ultimo_pedido = None
    return g.ultimo_pedido

def set_ultimo_pedido(valor):
    g.ultimo_pedido = valor
    with open('ultimo_pedido.pkl', 'wb') as f:
        pickle.dump(valor, f)

@employee_bp.route("/verificar_novos_pedidos")
def verificar_novos_pedidos():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT data_hora FROM pedidos ORDER BY data_hora DESC LIMIT 1")
        ultimo_pedido = cursor.fetchone()
        if not ultimo_pedido:
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
        return jsonify({"erro": f'Erro ao verificar novos pedidos {e}'}), 500
    finally:
        if conn:
            conn.close()