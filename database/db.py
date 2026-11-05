import os
import mysql.connector
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo data.env ubicado en la misma carpeta
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "data.env"))

def get_connection():
    # Establece y retorna una conexión segura a la base de datos MySQL
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),                # Host de la base de datos
        port=int(os.getenv("DB_PORT")),           # Puerto de conexión
        user=os.getenv("DB_USERNAME"),            # Usuario de la base de datos
        password=os.getenv("DB_PASSWORD"),        # Contraseña del usuario
        database=os.getenv("DB_DATABASE"),        # Nombre de la base de datos
        ssl_ca=os.path.join(os.path.dirname(__file__), "certs", "ca.pem")  # Ruta al certificado SSL
    )
    return conn