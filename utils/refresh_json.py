
import json
from utils.saver import _get_filename


def atualizar_pedidos_json(pedidos):

    arquivo = _get_filename()
    try:
        with open(arquivo, "w", encoding="utf-8") as f:
            json.dump(pedidos, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Erro ao atualizar pedidos no JSON: {e}")
        return False