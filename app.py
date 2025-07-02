from datetime import datetime
import uuid
import os
import pickle
from flask import Flask, g, json, redirect, render_template, render_template_string, request, jsonify, url_for
import requests
from utils.services import *
from utils.pdf_generator import gerar_pdf, PDFGenerationException
import traceback
import sqlite3

app = Flask(__name__)

# Configurações
DATABASE = 'pedidos.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
    return conn

ultimo_pedido = None
def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS pedidos (
                     id TEXT PRIMARY KEY NOT NULL,
                     cliente TEXT NOT NULL,
                     telefone TEXT DEFAULT '(XX) XXXXX-XXXX',
                     data_hora TEXT NOT NULL,
                     status TEXT DEFAULT 'pendente',
                     arquivo_pdf TEXT
                     )
                     ''')
        conn.execute('''CREATE TABLE IF NOT EXISTS itens (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     pedido_id TEXT NOT NULL,
                     item TEXT NOT NULL,
                     quantidade INTEGER NOT NULL,
                     unidade TEXT NOT NULL DEFAULT 'u',
                     FOREIGN KEY (pedido_id) REFERENCES pedidos (id) ON DELETE CASCADE
                     )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS foto_item (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     path TEXT NOT NULL,
                     pedido_id TEXT NOT NULL,
                     item_id INTEGER NOT NULL,
                     FOREIGN KEY (pedido_id) REFERENCES pedidos (id) ON DELETE CASCADE,
                     FOREIGN KEY (item_id) REFERENCES itens (id) ON DELETE CASCADE
                     )''')
        conn.commit()

@app.route("/",)
def index():
    nome = request.args.get("sucesso")
    return render_template("index.html",sucesso=nome)

@app.route("/pedido/<string:pedido_id>/excluir", methods=["DELETE"])
def excluir_pedido(pedido_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM pedidos WHERE id = ?', (pedido_id,))
        cursor.execute('DELETE FROM itens WHERE pedido_id = ?', (pedido_id,))
        cursor.execute('DELETE FROM foto_item WHERE pedido_id = ?', (pedido_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('painel'))
    except Exception as e:
        print("Erro ao excluir pedido:", traceback.format_exc())
        return jsonify({"erro": "Erro interno no servidor."}), 500


@app.route("/pedido/<string:pedido_id>/editar", methods=["GET"])
def view_editar_pedido(pedido_id):
    try:
        conn = sqlite3.connect(DATABASE)
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

@app.route("/pedido/<string:pedido_id>/editar", methods=["POST"])
def salver_editar_pedido(pedido_id):
    try:
        id = request.form.get('id')

        telefone = request.form.get('telefone')
        if not validar_telefone(telefone):
            return jsonify({'erro':'Formato de telefone inválido.'}), 400
        

        status = request.form.get('status')
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE pedidos SET telefone= ?, status = ?, data_hora = ? WHERE id = ?',(telefone,status,data_hora,id,))
        

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
            cursor.execute('UPDATE itens SET item= ?, quantidade = ? WHERE pedido_id = ?',(item['item'],item['quantidade'],id,))
        conn.commit() 
        conn.close()
        return redirect(url_for('painel'))
    except Exception as e:
        print("Erro ao editar pedido:", traceback.format_exc())
        return jsonify({"erro": "Erro interno no servidor."}), 500


@app.route("/pedido", methods=["POST"])
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
            'status': 'pendente'
        }
        caminho_pdf = gerar_pdf(pedido,mensagem)
        pedido['arquivo_pdf'] = caminho_pdf
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pedidos VALUES (:id, :cliente, :telefone, :data_hora, :status, :arquivo_pdf)",
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

@app.route("/painel")
def painel():
    status = request.args.get("status", "pendente")
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM pedidos WHERE status = ?", (status,))
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
                WHERE p.status = ? AND p.id = ?
                ORDER BY i.id
            """, (status, order_id))
            
            items_data = cursor.fetchall()
            
            itens_fotos = []
            current_item = None
            
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

@app.route("/cliente/enviar", methods=["POST"])
def cliente_enviar():
    cliente = request.form.get("cliente")
    telefone = request.form.get("telefone")
    mensagem = request.form.get("mensagem")
    fotos_salvas = []
    for key in request.files:
        file = request.files[key]
        if file and file.filename != '':
            caminho = f"static/fotos/{file.filename}"
            file.save(caminho)
            fotos_salvas.append(caminho)
    payload = {
        "cliente": cliente,
        "telefone": telefone,
        "mensagem": mensagem,
        "fotos": fotos_salvas
    }
    try:
        # Requisição local para a própria rota /pedido
        resposta = requests.post("http://localhost:5000/pedido", json=payload)

        if resposta.status_code == 200 or resposta.status_code == 201:
            return redirect(url_for("index",sucesso=cliente))
        else:
            return f"Erro ao enviar pedido: {resposta.json().get('erro')}", 400
    except Exception as e:
        return render_template_string(f"""
            <div style='padding: 20px;'>
              <h2>❌ Erro interno: {str(e)}</h2>
              <a href='/'>Tentar novamente</a>
            </div>
        """)

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

@app.route("/verificar_novos_pedidos")
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

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
