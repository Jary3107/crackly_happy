from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from database.db import get_connection
import bcrypt
import re

# Definir el blueprint para las rutas de administración
bp = Blueprint('admin', __name__, url_prefix='/admin')

# Ruta del dashboard de administrador
@bp.route('/dashboard')
def dashboard():
    # Verificar que el usuario sea admin
    if 'user_type' not in session or session['user_type'] != 'admin':
        flash('Acceso denegado', 'danger')
        return redirect(url_for('auth.login'))
    
    # Renderizar el dashboard de admin
    return render_template('admin/dashboard.html', nombre=session.get('nombre'))

# Ruta para registrar un nuevo usuario (GET y POST)
@bp.route('/registrar-usuario', methods=['GET', 'POST'])
def registrar_usuario():
    # Verificar que el usuario sea admin
    if 'user_type' not in session or session['user_type'] != 'admin':
        flash('Acceso denegado. Solo administradores pueden registrar usuarios.', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        # Obtener datos del formulario
        datos = {
            'nombre': request.form.get('nombre'),
            'cc': request.form.get('cc'),
            'telefono': request.form.get('telefono'),
            'correo': request.form.get('correo'),
            'rol': request.form.get('rol'),
            'contrasena': request.form.get('contrasena'),
            'direccion': request.form.get('direccion'),
            'municipio': request.form.get('municipio'),
            'departamento': request.form.get('departamento'),
            'sexo': request.form.get('sexo')
        }

        # Validar campos obligatorios
        if not all([datos['nombre'], datos['cc'], datos['correo'], datos['rol'], datos['contrasena']]):
            flash('Por favor completa todos los campos obligatorios', 'danger')
            return render_template('admin/registrar_usuario.html', datos=datos)

        # Validar que el rol sea permitido
        roles_validos = ['Comercial', 'Produccion', 'Facturacion', 'Admin']
        if datos['rol'] not in roles_validos:
            flash('Rol no válido', 'danger')
            return render_template('admin/registrar_usuario.html', datos=datos)

        # Validar formato de correo electrónico
        regex_correo = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(regex_correo, datos['correo']):
            flash("El correo ingresado no es válido", "danger")
            return render_template('admin/registrar_usuario.html', datos=datos)

        # Validar la seguridad de la contraseña
        contrasena = datos['contrasena']
        if len(contrasena) < 8 \
            or not re.search(r'[A-Z]', contrasena) \
            or not re.search(r'[a-z]', contrasena) \
            or not re.search(r'\d', contrasena) \
            or not re.search(r'[!@#$%^&*(),.?":{}|<>]', contrasena):
            flash("La contraseña debe tener mínimo 8 caracteres, incluyendo mayúscula, minúscula, número y un carácter especial", "danger")
            return render_template('admin/registrar_usuario.html', datos=datos)

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
                return render_template('admin/registrar_usuario.html', datos=datos)

            # Encriptar la contraseña antes de guardar
            contrasena_hash = bcrypt.hashpw(contrasena.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Insertar el nuevo usuario en la base de datos
            cursor.execute("""
                INSERT INTO Usuarios (nombre, cc, telefono, correo, rol, contrasena, direccion, municipio, departamento, sexo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (datos['nombre'], datos['cc'], datos['telefono'], datos['correo'], datos['rol'], 
                  contrasena_hash, datos['direccion'], datos['municipio'], datos['departamento'], datos['sexo']))

            conn.commit()
            cursor.close()
            conn.close()

            flash(f'Usuario {datos["nombre"]} registrado correctamente con rol {datos["rol"]}.', 'success')
            return redirect(url_for('admin.registrar_usuario'))

        except Exception as e:
            # Manejar errores de base de datos u otros
            flash(f"Error al registrar usuario: {str(e)}", 'danger')
            return render_template('admin/registrar_usuario.html', datos=datos)

    # Renderizar el formulario de registro de usuario (GET)
    return render_template('admin/registrar_usuario.html')