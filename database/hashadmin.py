import os
import mysql.connector
import bcrypt
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo data.env
load_dotenv(os.path.join(os.path.dirname(__file__), "data.env"))

# Función para hashear la contraseña usando bcrypt
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')  # Convertir bytes a string para almacenar

# Datos del administrador a insertar
admin = {
    "nombre": "Administrador",
    "cc": "0000000000",
    "telefono": "0000000000",
    "correo": "administracion@cracklyhappy.com",
    "contrasena": "Crujientementefelí782%",  # Contraseña fuerte
    "direccion": "N/A",
    "municipio": "Medellín",
    "departamento": "Antioquia",
    "sexo": "Masculino",
    "rol": "Admin"
}

# Conexión y ejecución del insert
try:
    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_DATABASE"),
        ssl_ca=os.path.join(os.path.dirname(__file__), "certs", "ca.pem")
    )
    
    cursor = connection.cursor()
    hashed_pw = hash_password(admin["contrasena"])
    
    query = """
    INSERT INTO Usuarios (
        nombre, cc, telefono, correo, contrasena, 
        direccion, municipio, departamento, sexo, rol
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    valores = (
        admin["nombre"],
        admin["cc"],
        admin["telefono"],
        admin["correo"],
        hashed_pw,
        admin["direccion"],
        admin["municipio"],
        admin["departamento"],
        admin["sexo"],
        admin["rol"]
    )
    
    cursor.execute(query, valores)
    connection.commit()
    
    print("✅ Administrador insertado correctamente con contraseña hasheada")
    
except mysql.connector.Error as e:
    print(f"❌ Error en la base de datos: {e}")
finally:
    if 'connection' in locals() and connection:
        connection.close()