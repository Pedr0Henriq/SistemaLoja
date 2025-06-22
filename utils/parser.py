# parser.py
import re
import unicodedata

class PedidoParsingException(Exception):
    pass

def normalize_text(texto):
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')

def parse_mensagem(mensagem):
    try:        
        mensagem = mensagem.replace("\\n", "\n")
        linhas = mensagem.strip().splitlines()
        pedido = []
        
        for linha in linhas:
            match = re.match(r"(\d+)\s*x\s*(.+)", linha, re.IGNORECASE)
            if match:
                qtd, item = match.groups()
                pedido.append({
                    "item": item.strip(),
                    "quantidade": int(qtd)
                })
        
        return pedido
    except Exception as e:
        raise PedidoParsingException("Falha ao interpretar o pedido.") from e
