from flask import Blueprint, render_template, redirect, url_for, flash, session
from database.db import get_connection
from flask import request, jsonify
import google.generativeai as genai
from datetime import datetime
import markdown2
import os
import re

# Definir el blueprint para las rutas de cliente
bp = Blueprint('cliente', __name__, url_prefix='/cliente')

def asegurar_carrito():
    if 'carrito' not in session or not isinstance(session['carrito'], list):
        session['carrito'] = []
    return session['carrito']

# Ruta del dashboard de cliente
@bp.route('/dashboard')
def dashboard():
    # Verificar que el usuario sea cliente
    if 'user_type' not in session or session['user_type'] != 'cliente':
        flash('Acceso denegado', 'danger')
        return redirect(url_for('auth.login'))
    
    # Renderizar el dashboard de cliente, pasando el nombre desde la sesión
    return render_template('cliente/dashboard.html', 
                         nombre=session.get('nombre'))

@bp.route('/informacion-empresa')
def informacion_empresa():
    # Verificar que el usuario sea cliente
    if 'user_type' not in session or session['user_type'] != 'cliente':
        flash('Acceso denegado', 'danger')
        return redirect(url_for('auth.login'))
    
    # Renderizar la página de información de la empresa
    return render_template('cliente/informacion_empresa.html',
                         nombre=session.get('nombre'))
    
@bp.route('/catalogo')
def catalogo_cliente():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT p.id_producto, p.nombre_producto, p.descripcion,
               p.precio, p.stock, p.imagen, l.nombre_linea
        FROM productos p
        LEFT JOIN lineas_producto l ON p.id_linea = l.id_linea
        ORDER BY l.nombre_linea, p.nombre_producto
    """)

    rows = cursor.fetchall()
    cursor.close()
    connection.close()

    # Agrupar productos por línea
    productos_por_linea = {}
    for p in rows:
        linea = p["nombre_linea"] or "Otros"
        productos_por_linea.setdefault(linea, []).append(p)

    return render_template("catalogo.html",
                           productos_por_linea=productos_por_linea,
                           publico=False)  


@bp.route('/producto/<int:id>')
def producto_detalle_cliente(id):
    # Verificar sesión
    if 'user_type' not in session or session['user_type'] != 'cliente':
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT p.*, l.nombre_linea
        FROM productos p
        LEFT JOIN lineas_producto l ON p.id_linea = l.id_linea
        WHERE p.id_producto = %s
    """, (id,))
    producto = cursor.fetchone()

    cursor.close()
    conn.close()

    if not producto:
        return "Producto no encontrado", 404

    # IMPORTANTE: ENVIAR publico = False
    return render_template("detalle_producto.html", producto=producto, publico=False)

def normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = texto.lower().strip()
    reemplazos = {
        "á":"a", "é":"e", "í":"i", "ó":"o", "ú":"u",
        "ü":"u", "ñ":"n"
    }
    for k,v in reemplazos.items():
        texto = texto.replace(k, v)
    return texto

def markdown_simple(text):
    if not text:
        return text

    # negrita **texto**
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)

    # cursiva *texto*
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)

    return text

@bp.route("/chatbot_respuesta", methods=["POST"]) 
def chatbot_respuesta():
    try:
        # Configurar el cliente de Gemini aquí para asegurar que la clave API se lee en cada solicitud
        # Es una buena práctica cargarla desde variables de entorno
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"respuesta": "Error: La clave API de Gemini no está configurada en el servidor."})
        genai.configure(api_key=api_key)

        data = request.get_json()
        mensaje = data.get("mensaje", "").strip()

        if not mensaje:
            return jsonify({"respuesta": "No recibí tu mensaje 😢"})

        # Mantener un saludo inicial, pero dirigir todas las demás preguntas a la IA
        if mensaje.lower() in ["hola", "menu", "menú", "opciones", "inicio"]:
            respuesta = (
                "¡Hola! Soy tu Asistente Virtual de Crackly Happy. 👋\n\n"
                "Puedes preguntarme sobre nuestros productos, precios, personalizaciones o cualquier otra duda que tengas."
            )
            return jsonify({"respuesta": respuesta})

        # Para cualquier otro mensaje, consultamos a la IA.
        # Primero, obtenemos el contexto de la base de datos.
        
        # Conectar a la BD para obtener contexto
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener líneas de productos
        cursor.execute("SELECT nombre_linea, descripcion FROM lineas_producto")
        lineas = cursor.fetchall()

        # Obtener productos
        cursor.execute("""
            SELECT p.nombre_producto, p.descripcion, p.precio, l.nombre_linea
            FROM productos p
            LEFT JOIN lineas_producto l ON p.id_linea = l.id_linea
        """)
        productos = cursor.fetchall()

        cursor.close()
        conn.close()

        # Construir el contexto para Gemini
        contexto_db = "Líneas de productos:\n"
        for linea in lineas:
            contexto_db += f"- {linea['nombre_linea']}: {linea['descripcion']}\n"

        contexto_db += "\nLista de productos y precios:\n"
        for p in productos:
            contexto_db += f"- {p['nombre_producto']} (Línea: {p['nombre_linea']}): ${p['precio']}. Descripción: {p['descripcion']}\n"

        # Información general estática para el prompt
        informacion_general = """
        --- INFORMACIÓN GENERAL DE LA EMPRESA ---
        - **Ubicación:** Estamos ubicados en Medellín. No tenemos punto físico, pero hacemos envíos.
        - **Horarios de atención:** Lunes a sábado de 8:00 a.m. a 7:00 p.m.
        - **Envíos:** Hacemos entregas en Medellín y envíos a toda Colombia.
        - **Métodos de pago:** Aceptamos Nequi, Daviplata, Bancolombia, transferencia bancaria y pagos contraentrega solo en Medellín.
        - **Personalizaciones:** Ofrecemos personalizaciones con nombres o frases, fotos, temáticas especiales, etiquetas y colores personalizados, y diseño corporativo. Para más detalles sobre personalizaciones, el cliente puede contactar por WhatsApp al 301345678 o al correo cracklyhappy@gmail.com.
        """

        # Crear el prompt para el modelo
        prompt = f"""
        Eres el Asistente Virtual de "Crackly Happy", una empresa que vende galletas de la fortuna.
        Tu objetivo es responder las preguntas de los clientes de forma amable y útil. Utiliza la siguiente información para responder.

        **Instrucciones especiales:**
        - Si el usuario pide ver el "catálogo", "productos", "galletas" o algo similar, responde únicamente con el texto: [ACTION:VIEW_CATALOG]
        - Si la pregunta no está relacionada con la empresa o sus productos, responde amablemente que solo puedes ayudar con temas de Crackly Happy.
        - Si no sabes la respuesta a una pregunta sobre la empresa, di que no tienes esa información y sugiere contactar a soporte.

        {informacion_general}

        --- CONTEXTO DE LA BASE DE DATOS ---
        {contexto_db}
        --- FIN DEL CONTEXTO ---

        Pregunta del cliente: "{mensaje}"

        Respuesta:
        """

        # Llamar a la API de Gemini
        model = genai.GenerativeModel('gemini-pro-latest') # Modelo corregido según los modelos disponibles
        response = model.generate_content(prompt)
        
        respuesta_texto = response.text.strip()

        # --- Manejo de acciones especiales ---
        if respuesta_texto == "[ACTION:VIEW_CATALOG]":
            # Si la IA nos pide mostrar el catálogo, creamos una respuesta con un botón
            return jsonify({
                "respuesta": "¡Claro! Aquí tienes nuestro catálogo de productos. Haz clic en el botón para explorarlo.",
                "botones": [
                    {"texto": "Ver Catálogo de Productos", "url": url_for('cliente.catalogo_cliente')}
                ]
            })

        return jsonify({"respuesta": respuesta_texto})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"respuesta": "Hubo un error inesperado. Intenta de nuevo."})




#---------- Añadir al carrito (POST desde form) ----------

@bp.route('/agregar_carrito', methods=['POST'])
def agregar_carrito():
    producto_id = request.form.get('producto_id')
    nombre = request.form.get('nombre')
    precio = request.form.get('precio')
    cantidad = request.form.get('cantidad', 1)

    # validaciones mínimas
    if not producto_id or not nombre or precio is None:
        flash('Datos del producto incompletos', 'danger')
        return redirect(request.referrer or url_for('cliente.catalogo_cliente'))

    try:
        precio = float(precio)
        cantidad = int(cantidad)
    except:
        flash('Precio o cantidad inválida', 'danger')
        return redirect(request.referrer or url_for('cliente.catalogo_cliente'))

    carrito = asegurar_carrito()

    # Buscar si ya está el producto (por id)
    encontrado = None
    for it in carrito:
        if str(it.get('producto_id')) == str(producto_id):
            encontrado = it
            break

    if encontrado:
        encontrado['cantidad'] = int(encontrado.get('cantidad', 1)) + cantidad
    else:
        # guardamos campos útiles en el carrito; puedes agregar más (imagen, descripcion...)
        carrito.append({
            'producto_id': int(producto_id),
            'nombre': nombre,
            'precio': precio,
            'cantidad': cantidad,
            # opcionales: imagen, descripcion, campos extras
            'imagen': request.form.get('imagen'),
            'descripcion': request.form.get('descripcion'),
            # campos personalizados para detalle_pedido (si aplica)
            'tiro_mensaje': request.form.get('tiro_mensaje'),
            'retiro_mensaje': request.form.get('retiro_mensaje'),
            'mensajes_mezclados': request.form.get('mensajes_mezclados'),
            'inserto': request.form.get('inserto'),
            'empaque': request.form.get('empaque'),
            'cenefa': request.form.get('cenefa'),
            'observacion': request.form.get('observacion')
        })

    session['carrito'] = carrito
    session.modified = True
    flash('Producto agregado al carrito correctamente', 'success')
    return redirect(request.referrer or url_for('cliente.catalogo_cliente'))

# ---------- Ver carrito ----------
@bp.route('/carrito')
def ver_carrito():
    carrito = session.get('carrito', [])
    total = sum(float(it['precio']) * int(it['cantidad']) for it in carrito) if carrito else 0

    datos_cliente = {
        'nombre': session.get('nombre', ''),
        'direccion': session.get('direccion', ''),
        'ciudad': session.get('ciudad', ''),
        'telefono': session.get('telefono', ''),
        'correo': session.get('correo', '')
    }

    return render_template(
        'cliente/carrito.html',
        carrito=carrito,
        total=total,
        datos_cliente=datos_cliente
    )

# ---------- Actualizar cantidad (form POST: action sumar/restar o cantidad directa) ----------
@bp.route('/actualizar_cantidad', methods=['POST'])
def actualizar_cantidad():
    producto_id = request.form.get('producto_id')
    accion = request.form.get('action')     # 'sumar' o 'restar' o None
    cantidad_val = request.form.get('cantidad')  # valor directo

    carrito = asegurar_carrito()

    for it in carrito:
        if str(it.get('producto_id')) == str(producto_id):
            if accion == 'sumar':
                it['cantidad'] = int(it.get('cantidad', 1)) + 1
            elif accion == 'restar':
                it['cantidad'] = max(1, int(it.get('cantidad', 1)) - 1)
            elif cantidad_val is not None:
                try:
                    q = int(cantidad_val)
                    it['cantidad'] = max(1, q)
                except:
                    pass
            break

    session['carrito'] = carrito
    session.modified = True
    return redirect(url_for('cliente.ver_carrito'))

# ---------- Eliminar item ----------
@bp.route('/eliminar_item/<int:producto_id>')
def eliminar_item(producto_id):
    carrito = session.get('carrito', [])
    carrito = [it for it in carrito if int(it.get('producto_id')) != int(producto_id)]
    session['carrito'] = carrito
    session.modified = True
    flash('Producto eliminado', 'success')
    return redirect(url_for('cliente.ver_carrito'))

@bp.route('/pedido/finalizar', methods=['GET'])
def mostrar_finalizar_pedido():
    carrito = session.get("carrito", [])
    total = sum(item["precio"] * item["cantidad"] for item in carrito)

    datos_cliente = {
        "nombre": session.get("nombre", ""),
        "direccion": session.get("direccion", ""),
        "ciudad": session.get("ciudad", ""),
        "telefono": session.get("telefono", "")
    }

    return render_template(
        "cliente/finalizar_pedido.html",
        carrito=carrito,
        total=total,
        datos_cliente=datos_cliente,
        publico=False
    )

@bp.route('/pedido/crear', methods=['POST'])
def crear_pedido():
    if 'user_id' not in session:
        flash("Debes iniciar sesión", "warning")
        return redirect(url_for('auth.login'))

    id_usuario = session['user_id']

    conn = get_connection()
    cursor = conn.cursor()

    # Buscar id_cliente correspondiente al usuario
    cursor.execute("SELECT id_cliente FROM clientes WHERE id_usuario = %s", (id_usuario,))
    row = cursor.fetchone()

    if not row:
        flash("Error: No existe un cliente asociado a este usuario.", "danger")
        return redirect(url_for('cliente.dashboard'))

    id_cliente = row[0]
    id_vendedor = 30001

    nombre_receptor = request.form.get('nombre_receptor')
    direccion_entrega = request.form.get('direccion_entrega')
    ciudad_entrega = request.form.get('ciudad_entrega')
    forma_pago = request.form.get('forma_pago')
    observaciones = request.form.get('observaciones')

    estado_pago = "Pagado" if forma_pago in ["Transferencia", "Tarjeta"] else "No Pagado"

    carrito = session.get("carrito", [])
    if not carrito:
        flash("Tu carrito está vacío.", "warning")
        return redirect(url_for('cliente.dashboard'))

    total = sum(item["precio"] * item["cantidad"] for item in carrito)

    try:
        # Generar número de pedido
        cursor.execute("SELECT COUNT(*) FROM pedidos")
        total_pedidos = cursor.fetchone()[0] + 1
        numero_pedido = f"PED-{datetime.now().year}-{total_pedidos:04d}"

        # Insertar pedido
        cursor.execute("""INSERT INTO pedidos (id_cliente, id_vendedor, numero_pedido, fecha_pedido, ciudad_entrega, direccion_entrega, forma_pago, estado, estado_pago, valor_total, observaciones) VALUES (%s, %s, %s, NOW(), %s, %s, %s, 'Pendiente', %s, %s, %s)""", (id_cliente, id_vendedor, numero_pedido, ciudad_entrega, direccion_entrega, forma_pago, estado_pago, total, observaciones))

        id_pedido = cursor.lastrowid

        # Insertar detalles del pedido
        for item in carrito:
            cursor.execute("""INSERT INTO detalle_pedido (id_pedido, id_producto, cantidad, precio_unitario, subtotal) VALUES (%s, %s, %s, %s, %s)""", (id_pedido, item["producto_id"], item["cantidad"], item["precio"], item["precio"] * item["cantidad"]))

        conn.commit()
        session["carrito"] = []

        flash("Pedido creado correctamente", "success")
        return redirect(url_for('cliente.ver_carrito'))

    except Exception as e:
        conn.rollback()
        flash(f"Error creando pedido: {e}", "danger")
        return redirect(url_for('cliente.ver_carrito'))

    finally:
        cursor.close()
        conn.close()

@bp.route('/perfil')
def perfil():
    # Validar sesión correctamente
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    id_usuario = session['user_id']

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Datos del usuario
    cursor.execute("SELECT * FROM usuarios WHERE id_usuario = %s", (id_usuario,))
    usuario = cursor.fetchone()

    # Datos del cliente
    cursor.execute("SELECT * FROM clientes WHERE id_usuario = %s", (id_usuario,))
    cliente = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template('cliente/perfil.html', usuario=usuario, cliente=cliente)

@bp.route('/perfil/actualizar', methods=['POST'])
def actualizar_perfil_cliente():
    if 'user_id' not in session:
        flash("Debes iniciar sesión", "warning")
        return redirect(url_for('auth.login'))

    id_usuario = session['user_id']

    # Datos recibidos del formulario
    nombre = request.form.get('nombre')
    telefono = request.form.get('telefono')
    direccion = request.form.get('direccion')
    municipio = request.form.get('municipio')
    departamento = request.form.get('departamento')

    # Datos tabla clientes
    tipo_cliente = request.form.get('tipo_cliente')
    razon_social = request.form.get('razon_social')
    nit_cc = request.form.get('nit_cc')
    ciudad = request.form.get('ciudad')
    contacto = request.form.get('contacto')
    telefono_contacto = request.form.get('telefono_contacto')

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Actualizar Usuarios
        cursor.execute("""UPDATE usuarios SET nombre = %s, telefono = %s, direccion = %s, municipio = %s, departamento = %s WHERE id_usuario = %s""", (nombre, telefono, direccion, municipio, departamento, id_usuario))

        # Actualizar Clientes
        cursor.execute("""UPDATE clientes SET tipo_cliente = %s, razon_social = %s, nit_cc = %s, ciudad = %s, contacto = %s, telefono_contacto = %s WHERE id_usuario = %s""", (tipo_cliente, razon_social, nit_cc, ciudad, contacto, telefono_contacto, id_usuario))

        conn.commit()
        
        # Actualizar los datos en la sesión
        session['nombre'] = nombre
        session['telefono'] = telefono
        session['direccion'] = direccion
        
        # Flash message que será mostrado en el template
        flash("Perfil actualizado correctamente", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Error actualizando perfil: {str(e)}", "danger")

    cursor.close()
    conn.close()

    return redirect(url_for('cliente.perfil'))

@bp.route('/mis-pedidos')
def mis_pedidos():
    if 'user_id' not in session:
        flash("Debes iniciar sesión", "warning")
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id_cliente FROM clientes WHERE id_usuario = %s", (session['user_id'],))
    row = cursor.fetchone()
    
    if not row:
        flash("Cliente no encontrado", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for('cliente.dashboard'))

    id_cliente = row['id_cliente']

   
    desde = request.args.get('fecha_desde')
    hasta = request.args.get('fecha_hasta')

    query = """
        SELECT 
            p.id_pedido, 
            p.fecha_pedido AS fecha, 
            p.valor_total AS total,
            p.estado,
            e.numero_guia
        FROM pedidos p
        LEFT JOIN envios e ON p.id_pedido = e.id_pedido
        WHERE p.id_cliente = %s
    """
    
    filtros = [id_cliente]

    if desde:
        query += " AND p.fecha_pedido >= %s"
        filtros.append(desde)

    if hasta:
        query += " AND p.fecha_pedido <= %s"
        filtros.append(hasta)

    query += " ORDER BY p.fecha_pedido DESC"

    cursor.execute(query, filtros)
    pedidos = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("cliente/mis_pedidos.html",
                           pedidos=pedidos,
                           fecha_desde=desde,
                           fecha_hasta=hasta)

@bp.route('/pedido/<int:id_pedido>')
def detalle_pedido(id_pedido):
    if 'user_id' not in session:
        flash("Debes iniciar sesión", "warning")
        return redirect(url_for('auth.login'))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Obtener datos del pedido
    cursor.execute("""SELECT id_pedido, fecha_pedido AS fecha, valor_total AS total FROM pedidos WHERE id_pedido = %s""", (id_pedido,))
    pedido = cursor.fetchone()

    if not pedido:
        flash("Pedido no encontrado", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for('cliente.mis_pedidos'))

    # Obtener productos del pedido
    cursor.execute("""SELECT dp.id_detalle, p.id_pedido, pr.nombre_producto, pr.descripcion, pr.imagen, dp.cantidad, dp.precio_unitario, (dp.cantidad * dp.precio_unitario) AS subtotal FROM detalle_pedido dp INNER JOIN pedidos p ON dp.id_pedido = p.id_pedido INNER JOIN productos pr ON dp.id_producto = pr.id_producto WHERE p.id_pedido = %s""", (id_pedido,))
    detalles = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "cliente/detalles_pedido.html",
        pedido=pedido,
        detalles=detalles
    )
