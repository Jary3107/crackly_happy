from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from database.db import get_connection
import bcrypt
import re
import secrets
from datetime import datetime, timedelta
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Cargar variables de entorno para configuración de correo y base de datos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, 'database', 'email.env'))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, 'database', 'data.env'))

# Definir el blueprint para autenticación
bp = Blueprint('auth', __name__)

# Ruta para registro de nuevos clientes
@bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        # Obtener datos del formulario
        datos = {
            'nombre': request.form.get('nombre'),
            'cc': request.form.get('cc'),
            'telefono': request.form.get('telefono'),
            'correo': request.form.get('correo'),
            'contrasena': request.form.get('contrasena'),
            'direccion': request.form.get('direccion'),
            'municipio': request.form.get('municipio'),
            'departamento': request.form.get('departamento'),
            'sexo': request.form.get('sexo')
        }

        # Validar campos obligatorios
        if not all([datos['nombre'], datos['cc'], datos['telefono'], datos['correo'], datos['contrasena']]):
            flash('Por favor completa todos los campos obligatorios', 'danger')
            return render_template('registro.html', datos=datos)

        # Validar formato de correo electrónico
        regex_correo = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(regex_correo, datos['correo']):
            flash("El correo ingresado no es válido", "danger")
            return render_template('registro.html', datos=datos)

        # Validar teléfono (solo números, mínimo 10 dígitos)
        if not datos['telefono'].isdigit() or len(datos['telefono']) < 10:
            flash("El teléfono debe contener solo números y tener al menos 10 dígitos", "danger")
            return render_template('registro.html', datos=datos)

        # Validar seguridad de la contraseña
        contrasena = datos['contrasena']
        if len(contrasena) < 8 \
            or not re.search(r'[A-Z]', contrasena) \
            or not re.search(r'[a-z]', contrasena) \
            or not re.search(r'\d', contrasena) \
            or not re.search(r'[!@#$%^&*(),.?\":{}|<>]', contrasena):
            flash("La contraseña debe tener mínimo 8 caracteres, incluyendo mayúscula, minúscula, número y un carácter especial", "danger")
            return render_template('registro.html', datos=datos)

        try:
            # Conectar a la base de datos
            conn = get_connection()
            cursor = conn.cursor()

            # Verificar si el correo o la cédula ya existen
            cursor.execute("SELECT correo, cc FROM Usuarios WHERE correo = %s OR cc = %s", (datos['correo'], datos['cc']))
            usuario_existente = cursor.fetchone()
            
            if usuario_existente:
                if datos['correo'] == usuario_existente[0]:
                    flash("El correo electrónico ya está registrado", "danger")
                elif datos['cc'] == usuario_existente[1]:
                    flash("La cédula ya está registrada", "danger")
                cursor.close()
                conn.close()
                return render_template('registro.html', datos=datos)

            # Encriptar la contraseña antes de guardar
            contrasena_hash = bcrypt.hashpw(contrasena.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Insertar el nuevo usuario como Cliente
            cursor.execute("""INSERT INTO Usuarios (nombre, cc, telefono, correo, contrasena, direccion, municipio, departamento, sexo, rol)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Cliente')
            """, (datos['nombre'], datos['cc'], datos['telefono'], datos['correo'], 
                  contrasena_hash, datos['direccion'], datos['municipio'], datos['departamento'], datos['sexo']))
            # OBTENER EL ID DEL USUARIO CREADO
            nuevo_usuario_id = cursor.lastrowid

            # INSERTAR AUTOMÁTICAMENTE EN CLIENTES
            cursor.execute("""
                INSERT INTO clientes 
                (id_usuario, tipo_cliente, razon_social, nit_cc, direccion, ciudad, telefono, correo, contacto, telefono_contacto)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                nuevo_usuario_id,
                'Persona',           
                datos['nombre'],     
                datos['cc'],        
                datos['direccion'],
                datos['municipio'], 
                datos['telefono'],
                datos['correo'],
                datos['nombre'],    
                datos['telefono']    
            ))
            conn.commit()
            cursor.close()
            conn.close()

            flash('Cliente registrado correctamente. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            flash(f"Error al registrar cliente: {str(e)}", 'danger')
            print(f"Error detallado: {str(e)}")  # Para debugging
            return render_template('registro.html', datos=datos)

    return render_template('registro.html')

# Ruta para login de usuarios
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo')
        contrasena = request.form.get('contrasena')

        if not correo or not contrasena:
            flash('Por favor completa todos los campos', 'danger')
            return render_template('login.html')

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Buscar usuario por correo
            cursor.execute("SELECT id_usuario, contrasena, nombre, rol FROM Usuarios WHERE correo = %s", (correo,))
            usuario = cursor.fetchone()

            if usuario:
                id_usuario, contrasena_hash, nombre, rol = usuario

                # Verificar contraseña nula
                if not contrasena_hash:
                    flash('Error en las credenciales', 'danger')
                    cursor.close()
                    conn.close()
                    return render_template('login.html')

                # Validar contraseña
                if bcrypt.checkpw(contrasena.encode('utf-8'), contrasena_hash.encode('utf-8')):
                    session.permanent = True
                    session['user_id'] = id_usuario
                    session['user_type'] = rol.lower() if rol else 'cliente'
                    session['nombre'] = nombre
                    session['fecha_inicio_sesion'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    #  Obtener id_cliente real
                    cursor.execute("SELECT id_cliente FROM clientes WHERE id_usuario = %s", (id_usuario,))
                    cliente = cursor.fetchone()
                    session['id_cliente'] = cliente[0] if cliente else None

                    cursor.close()
                    conn.close()

                    # Redirecciones por rol
                    if rol == 'Cliente':
                        return redirect(url_for('cliente.dashboard'))
                    elif rol == 'Comercial':
                        return redirect(url_for('comercial.dashboard'))
                    elif rol == 'Produccion':
                        return redirect(url_for('produccion.dashboard'))
                    elif rol == 'Facturacion':
                        return redirect(url_for('facturacion.dashboard'))
                    elif rol == 'Admin':
                        return redirect(url_for('admin.dashboard'))
                    else:
                        return redirect(url_for('cliente.dashboard'))
                else:
                    flash('Contraseña incorrecta', 'danger')

            else:
                flash('Correo no registrado', 'danger')

            cursor.close()
            conn.close()

        except Exception as e:
            flash(f"Error al validar los datos: {str(e)}", "danger")

    return render_template('login.html')

# Ruta para cerrar sesión
@bp.route('/logout')
def logout():
    user_type = session.get('user_type')
    if user_type == 'cliente':
        carrito = session.get('carrito', [])
    else:
        carrito = None
        
    session.clear()
    
    if carrito is not None:
        session['carrito'] = carrito

    response = redirect(url_for('auth.login'))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response

# Ruta para solicitar recuperación de contraseña
@bp.route('/recuperar-contrasena', methods=['GET', 'POST'])
def recuperar_contrasena():
    if request.method == 'POST':
        correo = request.form.get('correo')
        
        if not correo:
            flash("Por favor ingresa tu correo electrónico", "danger")
            return render_template('recuperar_contrasena.html')
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Buscar usuario por correo
            cursor.execute("SELECT id_usuario FROM Usuarios WHERE correo = %s", (correo,))
            usuario = cursor.fetchone()
            
            if not usuario:
                flash("Si tu correo está registrado, recibirás instrucciones para restablecer tu contraseña", "info")
                cursor.close()
                conn.close()
                return redirect(url_for('auth.login'))
            
            user_id = usuario[0]
            
            # Generar token único y fecha de expiración
            token = secrets.token_hex(16)
            fecha_expiracion = datetime.now() + timedelta(hours=1)
            
            # Eliminar tokens existentes para este usuario
            cursor.execute("DELETE FROM Tokens WHERE id_usuario = %s", (user_id,))
            
            # Insertar nuevo token
            cursor.execute("""
                INSERT INTO Tokens (id_usuario, token, fecha_expiracion)
                VALUES (%s, %s, %s)
            """, (user_id, token, fecha_expiracion))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # Enviar correo de recuperación
            correo_enviado = enviar_correo_recuperacion(correo, token)
            
            if correo_enviado:
                flash("Se ha enviado un correo con las instrucciones para restablecer tu contraseña", "success")
                return redirect(url_for('auth.login'))
            else:
               enlace = url_for('auth.restablecer_contrasena', token=token, _external=True)
               flash(f"No se pudo enviar el correo. Puedes usar este enlace para restablecer tu contraseña manualmente: {enlace}", "warning")
               return redirect(url_for('auth.recuperar_contrasena'))
            
        except Exception as e:
            flash(f"Ocurrió un error al procesar tu solicitud: {str(e)}", "danger")
            return render_template('recuperar_contrasena.html')
    
    return render_template('recuperar_contrasena.html')

# Ruta para restablecer la contraseña usando el token
@bp.route('/restablecer-contrasena/<token>', methods=['GET', 'POST'])
def restablecer_contrasena(token):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verificar token válido y no expirado
        cursor.execute("""SELECT id_usuario, fecha_expiracion FROM Tokens WHERE token = %s""", (token,))
        resultado = cursor.fetchone()
        
        if not resultado:
            flash("El enlace de recuperación no es válido o ha expirado", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for('auth.login'))
        
        id_usuario, fecha_expiracion = resultado
        
        # Verificar si el token ha expirado
        if datetime.now() > fecha_expiracion:
            cursor.execute("DELETE FROM Tokens WHERE token = %s", (token,))
            conn.commit()
            cursor.close()
            conn.close()
            flash("El enlace de recuperación ha expirado. Por favor solicita uno nuevo", "danger")
            return redirect(url_for('auth.recuperar_contrasena'))
        
        if request.method == 'POST':
            nueva_contrasena = request.form.get('nueva_contrasena')
            confirmar_contrasena = request.form.get('confirmar_contrasena')
            
            if not nueva_contrasena or not confirmar_contrasena:
                flash("Por favor completa todos los campos", "danger")
                cursor.close()
                conn.close()
                return render_template('reestablecer_contrasena.html', token=token)
            
            if nueva_contrasena != confirmar_contrasena:
                flash("Las contraseñas no coinciden", "danger")
                cursor.close()
                conn.close()
                return render_template('reestablecer_contrasena.html', token=token)
            
            # Validar requisitos de la contraseña
            if len(nueva_contrasena) < 8 \
                or not re.search(r'[A-Z]', nueva_contrasena) \
                or not re.search(r'[a-z]', nueva_contrasena) \
                or not re.search(r'\d', nueva_contrasena) \
                or not re.search(r'[!@#$%^&*(),.?\":{}|<>]', nueva_contrasena):
                flash("La contraseña debe tener mínimo 8 caracteres, incluyendo mayúscula, minúscula, número y un carácter especial", "danger")
                cursor.close()
                conn.close()
                return render_template('reestablecer_contrasena.html', token=token)
            
            # Encriptar nueva contraseña
            contrasena_hash = bcrypt.hashpw(nueva_contrasena.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cursor.execute("UPDATE Usuarios SET contrasena = %s WHERE id_usuario = %s", (contrasena_hash, id_usuario))
            
            # Eliminar el token usado
            cursor.execute("DELETE FROM Tokens WHERE token = %s", (token,))
            conn.commit()
            cursor.close()
            conn.close()
            
            flash("Tu contraseña ha sido actualizada correctamente. Ahora puedes iniciar sesión", "success")
            return redirect(url_for('auth.login'))
        
        cursor.close()
        conn.close()
        return render_template('reestablecer_contrasena.html', token=token)
        
    except Exception as e:
        print(f"Error en restablecer_contrasena: {str(e)}")  # Para debugging
        flash(f"Ocurrió un error al procesar tu solicitud. Por favor intenta nuevamente.", "danger")
        return redirect(url_for('auth.recuperar_contrasena'))

# Función auxiliar para enviar el correo de recuperación de contraseña
def enviar_correo_recuperacion(destinatario, token):
    # Cargar configuración desde variables de entorno
    email_host = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
    email_port = int(os.environ.get("EMAIL_PORT", 587))
    email_username = os.environ.get("EMAIL_USERNAME", "")
    email_password = os.environ.get("EMAIL_PASSWORD", "")
    
    # Validar que las credenciales estén configuradas
    if not email_username or not email_password or email_username == "tu_correo@gmail.com" or email_password == "tu_contraseña_de_aplicacion":
        print("ERROR: Credenciales de correo no configuradas correctamente")
        return False
    
    # Crear el enlace de recuperación
    enlace_recuperacion = url_for('auth.restablecer_contrasena', token=token, _external=True)
    
    # Configurar el mensaje (texto y HTML)
    mensaje = MIMEMultipart("alternative")
    mensaje["Subject"] = "Recuperación de contraseña - Crackly Happy"
    mensaje["From"] = email_username
    mensaje["To"] = destinatario
    
    texto_plano = f"""
    Hola,
    Has solicitado restablecer tu contraseña en Crackly Happy.
    Para crear una nueva contraseña, haz clic en el siguiente enlace:
    {enlace_recuperacion}
    Este enlace expirará en 1 hora.
    Si no solicitaste restablecer tu contraseña, puedes ignorar este correo.
    Saludos,
    El equipo de Crackly Happy
    """
    
    html = f"""<html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #000000; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #dc2626; color: white; padding: 15px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ padding: 25px; border: 2px solid #e5e7eb; border-radius: 0 0 8px 8px; background-color: #ffffff; }}
            .button {{ display: inline-block; background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: bold; font-size: 16px; border: none; cursor: pointer; }}
            .button:hover {{ background-color: #0056b3; }}
            .footer {{ font-size: 12px; color: #6b7280; margin-top: 25px; padding-top: 15px; border-top: 1px solid #e5e7eb; }}
            .link {{ color: #007bff; word-break: break-all; }}
            p {{ color: #000000; }}
            h2, h3 {{ color: #000000; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 style="color: white; margin: 0;">Crackly Happy</h2>
            </div>
            <div class="content">
                <p><strong>Hola,</strong></p>
                <p>Has solicitado restablecer tu contraseña en Crackly Happy.</p>
                <p>Para crear una nueva contraseña, haz clic en el siguiente botón:</p>
                <p style="text-align: center;">
                    <a href="{enlace_recuperacion}" class="button">Restablecer contraseña</a>
                </p>
                <p>O copia y pega el siguiente enlace en tu navegador:</p>
                <p><a href="{enlace_recuperacion}" class="link">{enlace_recuperacion}</a></p>
                <p><strong>Este enlace expirará en 1 hora.</strong></p>
                <p>Si no solicitaste restablecer tu contraseña, puedes ignorar este correo.</p>
                <p>Saludos,<br><strong>El equipo de Crackly Happy</strong></p>
            </div>
            <div class="footer">
                <p>Este es un correo automático, por favor no respondas a este mensaje.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Adjuntar partes al mensaje
    parte_texto = MIMEText(texto_plano, "plain", "utf-8")
    parte_html = MIMEText(html, "html", "utf-8")
    mensaje.attach(parte_texto)
    mensaje.attach(parte_html)
    
    try:
        print(f"📤 Intentando enviar correo desde {email_username} a {destinatario} usando {email_host}:{email_port}")
        servidor = smtplib.SMTP(email_host, email_port, timeout=10)
        servidor.set_debuglevel(1)  # Muestra detalles del envío SMTP
        servidor.starttls()
        servidor.login(email_username, email_password)
        servidor.sendmail(email_username, destinatario, mensaje.as_string().encode("utf-8"))
        servidor.quit()
        print("✅ Correo enviado exitosamente.")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Error de autenticación SMTP: {e.smtp_error.decode() if hasattr(e, 'smtp_error') else str(e)}")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ Error SMTP general: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado al enviar correo: {str(e)}")
        return False