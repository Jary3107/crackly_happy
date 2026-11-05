import os
from flask_mail import Mail
from dotenv import load_dotenv  # 👈 importa dotenv

# Cargar variables desde el archivo .env
load_dotenv(os.path.join(os.path.dirname(__file__), 'email.env'))

mail = Mail()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'clave_super_secreta')

    MAIL_SERVER = os.getenv('EMAIL_HOST')
    MAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.getenv('EMAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = ('Sistema de Facturación', os.getenv('EMAIL_USERNAME'))