from flask import Flask, render_template
from controllers.auth_controller import bp as auth_bp
from controllers.admin_controller import bp as admin_bp
from controllers.cliente_controller import bp as cliente_bp
from controllers.comercial_controller import bp as comercial_bp
from controllers.facturacion_controller import bp as facturacion_bp
from controllers.produccion_controller import bp as produccion_bp
from controllers.public_controller import public  
from datetime import timedelta
from dotenv import load_dotenv
import os
from config import Config
from extensions import mail

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Crear la instancia principal de la aplicación Flask
app = Flask(__name__)
app.config.from_object(Config)

# Inicializar Flask-Mail
mail.init_app(app)

# Configurar la clave secreta de la aplicación (para sesiones y seguridad)
app.secret_key = os.getenv('SECRET_KEY', 'xxx')

# Configurar la duración de la sesión (15 minutos)
app.permanent_session_lifetime = timedelta(minutes=15)

# Ruta principal que renderiza la página de inicio
@app.route('/')
def inicio():
    return render_template('inicio.html')


# Registrar los blueprints para modularizar la aplicación
app.register_blueprint(auth_bp, url_prefix='')         # Autenticación
app.register_blueprint(admin_bp)                       # Administración
app.register_blueprint(cliente_bp)                     # Clientes
app.register_blueprint(comercial_bp)                   # Comercial
app.register_blueprint(facturacion_bp)                 # Facturación
app.register_blueprint(produccion_bp)                  # Producción
app.register_blueprint(public)                         # Rutas públicas
# Evitar que se cacheen páginas protegidas agregando encabezados HTTP
@app.after_request
def agregar_encabezados(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Ejecutar la aplicación en modo desarrollo si este archivo es el principal
if __name__ == '__main__':
    app.run(debug=True)
