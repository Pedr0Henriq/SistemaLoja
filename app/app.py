from flask import Flask
from database.database import init_db
from routes.client import client_bp
from routes.crud_order import crud_bp
from routes.api_whatsapp import whatsapp_bp
from routes.employee import employee_bp

app = Flask(__name__)

app.register_blueprint(client_bp)
app.register_blueprint(crud_bp)
app.register_blueprint(whatsapp_bp)
app.register_blueprint(employee_bp)

if __name__ == "__main__":
    init_db()
    app.run(host = "0.0.0.0", port= 5000, debug=True)
