from flask import Blueprint, render_template, render_template_string, request, jsonify, redirect, url_for
import requests


client_bp = Blueprint('client', __name__)

@client_bp.route("/",)
def index():
    nome = request.args.get("sucesso")
    return render_template("index.html",sucesso=nome)


@client_bp.route("/cliente/enviar", methods=["POST"])
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