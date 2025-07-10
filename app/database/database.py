import sqlite3


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
                     valor_total REAL DEFAULT 0.0
                     )
                     ''')
        conn.execute('''CREATE TABLE IF NOT EXISTS itens (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     pedido_id TEXT NOT NULL,
                     item TEXT NOT NULL,
                     quantidade REAL NOT NULL,
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