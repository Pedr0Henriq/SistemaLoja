import os
from flask import jsonify
import re
import unicodedata
from utils.enum import Unidades

class PedidoParsingException(Exception):
    pass


def parse_mensagem(mensagem):
    try:        
        mensagem = mensagem.replace("\\n", "\n")
        linhas = mensagem.strip().splitlines()
        pedido = []
        
        for linha in linhas:
            match = re.match(r"^(\d+(?:,\d{1,2})?)([muc])\sx\s([a-zA-ZÀ-ÿ0-9º°\-\s]+)$", linha, re.IGNORECASE)
            if match:
                qtd, unidade, item = match.groups()
                unidade = unidade.lower()
                if Unidades.is_valid(unidade):
                    pedido.append({
                        "item": item.strip(),
                        "quantidade": float(qtd.replace(',', '.')),
                        "unidade": Unidades[unidade].value
                    })
                else:
                    raise PedidoParsingException(f"Unidade inválida: {unidade}. Use as opções: m (metro), c (centímetro), u (unidade).")
        
        return pedido
    except Exception as e:
        raise PedidoParsingException("Falha ao interpretar o pedido.") from e
    
    
def validar_telefone(telefone):
    """Valida telefone no formato (XX) XXXX-XXXX ou (XX) XXXXX-XXXX"""
    padrao = re.compile(r'^\(\d{2}\) \d{4,5}-\d{4}$')
    return bool(padrao.match(telefone))


def excluir_anexos(fotos: list):    
    for foto in fotos:
        caminho_foto = foto
        try:
            if os.path.exists(caminho_foto):
                os.remove(caminho_foto)
                print(f"Arquivo {caminho_foto} excluído com sucesso.")
        except FileNotFoundError:
            raise FileNotFoundError(f"Arquivo {caminho_foto} não encontrado.")