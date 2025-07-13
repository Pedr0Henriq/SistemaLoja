# 🛒 Sistema de Pedidos Online

Sistema de pedidos online desenvolvido em **Python**, com integração à **Evolution API**. Permite o registro de pedidos, envio de mensagens via WhatsApp e painel web para visualização em tempo real pelos funcionários.

## 🚀 Funcionalidades

- Cadastro de pedidos com:
  - Nome do cliente
  - Itens pedidos
  - Imagens opcionais
- Armazenamento dos pedidos em  sqlite3
- Envio automático de mensagem no WhatsApp para o cliente
- Painel Web:
  - Filtro por data e cliente
  - Atualização em tempo real via JavaScript (sem recarregar)
  - Marcação do status do pedido (Pendente → Pagamento → Retirada → Entregue)
- Upload de imagens via multipart/form-data

## 🧰 Tecnologias Utilizadas

- **Python 3**
- **Flask** (API e Web Server)
- **Jinja2** (Templates HTML)
- **JavaScript** (atualizações dinâmicas no painel)
- **Bootstrap** (estilização)
- **Evolution API** (envio de mensagens via WhatsApp)

## ⚙️ Como Executar Localmente

### 1. Clone o projeto

```bash
git clone https://github.com/seu-usuario/sistema-pedidos-online.git
cd sistema-pedidos-online
```
### 2. Instale as dependências
```bash
pip install -r requirements.txt
```
### 3. Configure as variáveis de ambiente
``` bash
Crie um arquivo .env na raiz com o seguinte conteúdo:
EVOLUTION_API_KEY=seu_token_aqui
WHATSAPP_DDD_PADRAO=81
```
### 4. Execute o servidor
```bash
python app.py
