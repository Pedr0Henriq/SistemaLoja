from datetime import datetime
import uuid
from flask import Flask, json, redirect, render_template, render_template_string, request, jsonify, url_for
import requests
from utils import edit_func
from utils.parser import parse_mensagem, PedidoParsingException
from utils.pdf_generator import gerar_pdf, PDFGenerationException
import traceback

from utils.refresh_json import atualizar_pedidos_json
from utils.saver import salvar_pedido_json, carregar_pedidos_json

app = Flask(__name__)


@app.route("/pedido/<string:pedido_id>/excluir", methods=["DELETE"])
def excluir_pedido(pedido_id):
    try:
        pedidos = carregar_pedidos_json(pedido_id=pedido_id,excluir_id=True)        
        if atualizar_pedidos_json(pedidos):
            return redirect(url_for("painel"))
        else:
            return jsonify({"erro": "Erro ao excluir pedido."}), 500
    except Exception as e:
        print("Erro ao excluir pedido:", traceback.format_exc())
        return jsonify({"erro": "Erro interno no servidor."}), 500


@app.route("/pedido/<string:pedido_id>/editar", methods=["GET"])
def view_editar_pedido(pedido_id):
    try:
        pedidos = carregar_pedidos_json()
        pedido = next((p for p in pedidos if p.get("id") == pedido_id),None)
        if not pedido:
            return jsonify({"erro": "Pedido não encontrado."}), 404
        return render_template("edit_order.html", pedido = pedido)
    except Exception as e:
        print("Erro ao editar pedido:", traceback.format_exc())
        return jsonify({"erro": "Erro interno no servidor."}), 500

@app.route("/pedido/<string:pedido_id>/editar", methods=["POST"])
def salver_editar_pedido(pedido_id):
    try:
        pedidos = carregar_pedidos_json()
        pedido_index = next((i for i, p in enumerate(pedidos) if p["id"] == pedido_id), None)
        if pedido_index is None:
            return jsonify({"erro": "Pedido não encontrado."}), 404
        
        novos_itens = []
        i = 0
        while True:
            if f"itens[{i}][item]" not in request.form:
                break
            novos_itens.append({
                "item": request.form[f"itens[{i}][item]"],
                "quantidade": request.form.get(f"itens[{i}][quantidade]", 1, type=int),
            })
            i+=1
        
        pedidos[pedido_index]["itens"] = novos_itens
        atualizar_pedidos_json(pedidos)
        return render_template("view.html", pedidos=pedidos)
    except Exception as e:
        print("Erro ao editar pedido:", traceback.format_exc())
        return jsonify({"erro": "Erro interno no servidor."}), 500


@app.route("/pedido", methods=["POST"])
def receber_pedido():
    try:
        data = request.get_json(force=True)
        id = str(uuid.uuid4())
        data["id"] = id
        cliente = data.get("cliente")
        mensagem = data.get("mensagem")
        telefone = data.get("telefone")

        if not cliente:
            raise ValueError("Preencha o nome do cliente.")
        if not mensagem:
            raise ValueError("Preencha a mensagem do pedido.")
        if not telefone or not telefone.isdigit() or len(telefone) < 10:
            raise ValueError("Telefone inválido. Deve conter apenas números e ter pelo menos 10 dígitos.")
        if not isinstance(cliente, str) or not isinstance(mensagem, str):
            raise ValueError("Cliente e mensagem devem ser strings.")

        pedido = parse_mensagem(mensagem)
        if not pedido:
            raise PedidoParsingException("Não foi possível interpretar os itens do pedido.")

        caminho_pdf = gerar_pdf(id, pedido, cliente,telefone_cliente=telefone)
        salvar_pedido_json(id, cliente, pedido,telefone)
        return jsonify({
            "mensagem": "Pedido processado com sucesso.",
            "pdf_path": caminho_pdf
        })

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
    cliente = request.args.get("cliente", "").lower()
    pedidos = carregar_pedidos_json()
    if cliente:
        pedidos = [p for p in pedidos if cliente in p.get("cliente","").lower()]
    return render_template("view.html", pedidos=pedidos, current_date=datetime.now().strftime("%d-%m-%Y"))


@app.route("/",)
def index():
    nome = request.args.get("sucesso")
    return render_template("index.html",sucesso=nome)


@app.route("/cliente/enviar", methods=["POST"])
def cliente_enviar():
    cliente = request.form.get("cliente")
    telefone = request.form.get("telefone")
    mensagem = request.form.get("mensagem")

    payload = {
        "cliente": cliente,
        "telefone": telefone,
        "mensagem": mensagem
    }

    try:
        # Requisição local para a própria rota /pedido
        resposta = requests.post("http://localhost:5000/pedido", json=payload)

        if resposta.status_code == 200:
            return redirect(url_for("index",sucesso=cliente))
        else:
            return f"Erro ao enviar pedido: {resposta.json().get('erro')}", 400
    except Exception as e:
        return render_template_string(f"""
            <div style='padding: 20px;'>
              <h2>❌ Erro interno: {str(e)}</h2>
              <a href='/cliente'>Tentar novamente</a>
            </div>
        """)
    
if __name__ == "__main__":
    app.run(debug=True)
