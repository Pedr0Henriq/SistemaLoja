# utils.py
import os
import json
from datetime import datetime

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

def _get_filename():
    data_str = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(LOG_DIR, f"pedidos_{data_str}.json")

def salvar_pedido_json(id,cliente, itens,telefone_cliente):
    arquivo = _get_filename()
    novo_pedido = {
        "id": id,
        "cliente": cliente,
        "telefone": telefone_cliente,
        "itens": itens,
        "data_hora": datetime.now().isoformat(timespec='seconds')
    }

    try:
        if os.path.exists(arquivo):
            with open(arquivo, "r", encoding="utf-8") as f:
                pedidos = json.load(f)
        else:
            pedidos = []
        pedidos.append(novo_pedido)
        with open(arquivo, "w", encoding="utf-8") as f:
            json.dump(pedidos, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar pedido no JSON: {e}")


import os
import json

def carregar_pedidos_json(pedido_id=None, excluir_id=False):

    arquivo = _get_filename()
    if not os.path.exists(arquivo):
        return []

    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            pedidos = json.load(f)

        if pedido_id:
            if excluir_id:
                return [p for p in pedidos if p.get("id") != pedido_id]
            else:
                return next((p for p in pedidos if p.get("id") == pedido_id), None)
        
        return pedidos

    except Exception as e:
        print(f"Erro ao carregar pedidos do JSON: {e}")
        return []
