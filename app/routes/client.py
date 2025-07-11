import base64
import re
import uuid
from flask import Blueprint, render_template, render_template_string, request, jsonify, redirect, url_for
import requests, os
from uuid import uuid4
from werkzeug.utils import secure_filename


client_bp = Blueprint('client', __name__)

@client_bp.route("/",)
def index():
    nome = request.args.get("sucesso")
    return render_template("index.html",sucesso=nome)


@client_bp.route("/cliente/enviar", methods=["POST"])
def cliente_enviar():
    data = request.get_json()
    if not data:
        return jsonify({"erro": "JSON inválido"}), 400

    cliente = data.get("cliente")
    telefone = data.get("telefone")
    mensagem = data.get("mensagem")
    itens = data.get("itens", [])

    if not cliente or not telefone or not itens:
        return jsonify({"erro": "Campos obrigatórios faltando"}), 400

    UPLOAD_FOLDER = "static/fotos"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    fotos_salvas = []

    try:
        for idx, item in enumerate(itens):
            fotos_base64 = item.get("fotos", [])
            fotos_caminhos = []
            for i,foto_base64 in enumerate(fotos_base64):
                match = re.match(r'data:(image/\w+);base64,(.+)', foto_base64)
                if not match:
                    continue  # ignora caso formato inválido

                tipo_imagem, dados_base64 = match.groups()
                extensao = tipo_imagem.split('/')[-1]

                nome_arquivo = f"{uuid.uuid4().hex}_{idx}_{i}.{extensao}"
                caminho_arquivo = os.path.join(UPLOAD_FOLDER, nome_arquivo)

                with open(caminho_arquivo, "wb") as f:
                    f.write(base64.b64decode(dados_base64))

                fotos_caminhos.append(caminho_arquivo)

            fotos_salvas.append({
                "item_nome": item.get("nome"),
                "fotos": fotos_caminhos
            })
        print(f"[FOTOS SALVAS] {fotos_salvas}", flush=True)
    except Exception as e:
        return render_template_string("""
            <div style='padding: 20px; font-family: sans-serif;'>
            <h2>❌ Erro ao salvar fotos</h2>
            <p>Não foi possível salvar as fotos do pedido.</p>
            <p>Erro: {{ erro }}</p>
            <a href='/'>Tentar novamente</a>
            </div>
        """, erro=str(e))
    payload = {
        "cliente": cliente,
        "telefone": telefone,
        "mensagem": mensagem,
        "fotos": fotos_salvas
    }
    try:
        resposta = requests.post("http://localhost:5000/pedido", json=payload)

        if resposta.ok:
            return redirect(url_for("client.index",sucesso=cliente))
        else:
            return f"Erro ao enviar pedido: {resposta.json().get('erro')}", 400
    except Exception as e:
        return render_template_string("""
            <div style='padding: 20px; font-family: sans-serif;'>
            <h2>❌ Erro inesperado</h2>
            <p>Algo deu errado ao enviar seu pedido.</p>
            <p>Por favor, tente novamente ou entre em contato com o suporte.</p>
            <a href='/'>Tentar novamente</a>
            </div>
        """)