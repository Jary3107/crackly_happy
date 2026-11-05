from flask import Blueprint, render_template, redirect, url_for, flash, session, request, jsonify
from database.db import get_connection
from datetime import datetime

# Definir el blueprint para las rutas de comercial
bp = Blueprint('comercial', __name__, url_prefix='/comercial')

# Ruta del dashboard de comercial
@bp.route('/dashboard')
def dashboard():
    # Verificar que el usuario sea comercial
    if 'user_type' not in session or session['user_type'] != 'comercial':
        flash('Acceso denegado', 'danger')
        return redirect(url_for('auth.login'))
    
    # Renderizar el dashboard de comercial, pasando el nombre y el rol desde la sesión
    return render_template('comercial/dashboard.html', 
                         nombre=session.get('nombre'), 
                         rol='Comercial')

# Ruta para ver pedidos
@bp.route('/pedidos')
def ver_pedidos():
    # Verificar que el usuario sea comercial
    if 'user_type' not in session or session['user_type'] != 'comercial':
        flash('Acceso denegado', 'danger')
        return redirect(url_for('auth.login'))
    
    sort_by = request.args.get('sort_by', 'fecha')  # 'fecha' or 'cliente'
    order = request.args.get('order', 'desc')  # 'asc' or 'desc'
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')
    filtro_estado = request.args.get('filtro_estado', '')
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        query = """
            SELECT 
                p.id_pedido,
                p.numero_pedido,
                p.fecha_pedido,
                p.estado,
                p.estado_pago,
                p.valor_total,
                p.forma_pago,
                c.razon_social,
                c.ciudad as ciudad_cliente,
                p.ciudad_entrega
            FROM pedidos p
            INNER JOIN clientes c ON p.id_cliente = c.id_cliente
            WHERE 1=1
        """
        
        params = []
        
        if filtro_estado:
            query += " AND p.estado = %s"
            params.append(filtro_estado)
        else:
            query += " AND p.estado != 'Archivado'"
        
        if fecha_desde:
            query += " AND p.fecha_pedido >= %s"
            params.append(fecha_desde)
        
        if fecha_hasta:
            query += " AND p.fecha_pedido <= %s"
            params.append(fecha_hasta)
        
        if sort_by == 'cliente':
            query += f" ORDER BY c.razon_social {order.upper()}"
        else:  # sort by fecha
            query += f" ORDER BY p.fecha_pedido {order.upper()}"
        
        cursor.execute(query, params)
        pedidos = cursor.fetchall()
        
        if filtro_estado or fecha_desde or fecha_hasta or request.args.get('sort_by') or request.args.get('order'):
            flash('Filtro aplicado con éxito', 'success_programados')
        
    except Exception as e:
        flash(f'Error al cargar pedidos: {str(e)}', 'danger')
        pedidos = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('comercial/ver_pedidos.html',
                         nombre=session.get('nombre'),
                         pedidos=pedidos,
                         sort_by=sort_by,
                         order=order,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta,
                         filtro_estado=filtro_estado)

# Ruta para ver pedidos pagados
@bp.route('/pedidos-pagados')
def ver_pedidos_pagados():
    # Verificar que el usuario sea comercial
    if 'user_type' not in session or session['user_type'] != 'comercial':
        flash('Acceso denegado', 'danger')
        return redirect(url_for('auth.login'))
    
    sort_by = request.args.get('sort_by', 'fecha')  # 'fecha' or 'cliente'
    order = request.args.get('order', 'desc')  # 'asc' or 'desc'
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        query = """
            SELECT 
                p.id_pedido,
                p.numero_pedido,
                p.fecha_pedido,
                p.estado,
                p.estado_pago,
                p.valor_total,
                p.forma_pago,
                c.razon_social,
                c.ciudad as ciudad_cliente,
                p.ciudad_entrega
            FROM pedidos p
            INNER JOIN clientes c ON p.id_cliente = c.id_cliente
            WHERE p.estado_pago = 'Pagado'
        """
        
        params = []
        
        if fecha_desde:
            query += " AND p.fecha_pedido >= %s"
            params.append(fecha_desde)
        
        if fecha_hasta:
            query += " AND p.fecha_pedido <= %s"
            params.append(fecha_hasta)
        
        if sort_by == 'cliente':
            query += f" ORDER BY c.razon_social {order.upper()}"
        else:  # sort by fecha
            query += f" ORDER BY p.fecha_pedido {order.upper()}"
        
        cursor.execute(query, params)
        pedidos = cursor.fetchall()
        
        if fecha_desde or fecha_hasta or request.args.get('sort_by') or request.args.get('order'):
            flash('Filtro aplicado con éxito', 'success_pagados')
        
    except Exception as e:
        flash(f'Error al cargar pedidos pagados: {str(e)}', 'danger')
        pedidos = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('comercial/ver_pedidos_pagados.html',
                         nombre=session.get('nombre'),
                         pedidos=pedidos,
                         sort_by=sort_by,
                         order=order,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta)

@bp.route('/pedido/<int:id_pedido>')
def detalle_pedido(id_pedido):
    # Verificar que el usuario sea comercial
    if 'user_type' not in session or session['user_type'] != 'comercial':
        flash('Acceso denegado', 'danger')
        return redirect(url_for('auth.login'))
    
    from_page = request.args.get('from', '')
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""SELECT 
                p.*,
                c.razon_social,
                c.nit_cc,
                c.tipo_cliente,
                c.direccion as direccion_cliente,
                c.ciudad as ciudad_cliente,
                c.telefono,
                c.correo,
                c.contacto,
                c.telefono_contacto,
                u.nombre as nombre_vendedor
            FROM pedidos p
            INNER JOIN clientes c ON p.id_cliente = c.id_cliente
            LEFT JOIN usuarios u ON p.id_vendedor = u.id_usuario
            WHERE p.id_pedido = %s
        """, (id_pedido,))
        pedido = cursor.fetchone()
        
        if not pedido:
            flash('Pedido no encontrado', 'warning')
            return redirect(url_for('comercial.ver_pedidos'))
        
        cursor.execute("""SELECT 
                dp.*,
                pr.nombre_producto,
                lp.nombre_linea
            FROM detalle_pedido dp
            INNER JOIN productos pr ON dp.id_producto = pr.id_producto
            LEFT JOIN lineas_producto lp ON pr.id_linea = lp.id_linea
            WHERE dp.id_pedido = %s
        """, (id_pedido,))
        detalle = cursor.fetchall()
        
        cursor.execute("""SELECT * FROM envios WHERE id_pedido = %s
        """, (id_pedido,))
        envio = cursor.fetchone()
        
    except Exception as e:
        flash(f'Error al cargar el pedido: {str(e)}', 'danger')
        return redirect(url_for('comercial.ver_pedidos'))
    finally:
        cursor.close()
        conn.close()
    
    return render_template('comercial/detalle_pedido.html',
                         nombre=session.get('nombre'),
                         pedido=pedido,
                         detalle=detalle,
                         envio=envio,
                         from_page=from_page)

@bp.route('/registrar-pedido', methods=['GET'])
def registrar_pedido():
    # Verificar que el usuario sea comercial
    if 'user_type' not in session or session['user_type'] != 'comercial':
        flash('Acceso denegado', 'danger')
        return redirect(url_for('auth.login'))
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT id_cliente, razon_social, tipo_cliente FROM clientes ORDER BY razon_social")
        clientes = cursor.fetchall()
        
        cursor.execute("SELECT id_linea, nombre_linea FROM lineas_producto ORDER BY nombre_linea")
        lineas_producto = cursor.fetchall()
        
        cursor.execute("""SELECT p.id_producto, p.nombre_producto, p.precio, l.nombre_linea, p.id_linea
            FROM productos p
            LEFT JOIN lineas_producto l ON p.id_linea = l.id_linea
            ORDER BY p.nombre_producto
        """)
        productos = cursor.fetchall()
        
    except Exception as e:
        flash(f'Error al cargar datos: {str(e)}', 'danger')
        clientes = []
        lineas_producto = []
        productos = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('comercial/registrar_pedido.html',
                         nombre=session.get('nombre'),
                         clientes=clientes,
                         lineas_producto=lineas_producto,
                         productos=productos)

@bp.route('/registrar-pedido', methods=['POST'])
def guardar_pedido():
    # Verificar que el usuario sea comercial
    if 'user_type' not in session or session['user_type'] != 'comercial':
        flash('Acceso denegado', 'danger')
        return redirect(url_for('auth.login'))
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        errors = []
        
        tipo_cliente_seleccion = request.form.get('tipo_cliente_seleccion')
        
        # Validate client selection
        if tipo_cliente_seleccion == 'nuevo':
            required_new_client_fields = {
                'nueva_razon_social': 'Razón Social',
                'nuevo_nit_cc': 'NIT/CC',
                'nuevo_tipo_cliente': 'Tipo de Cliente',
                'nueva_ciudad': 'Ciudad',
                'nueva_direccion': 'Dirección',
                'nuevo_telefono': 'Teléfono'
            }
            
            for field, label in required_new_client_fields.items():
                if not request.form.get(field):
                    errors.append(f'El campo {label} es obligatorio')
            
            if not errors:
                nueva_razon_social = request.form.get('nueva_razon_social')
                nuevo_nit_cc = request.form.get('nuevo_nit_cc')
                nuevo_tipo_cliente = request.form.get('nuevo_tipo_cliente')
                nueva_ciudad = request.form.get('nueva_ciudad')
                nueva_direccion = request.form.get('nueva_direccion')
                nuevo_telefono = request.form.get('nuevo_telefono')
                nuevo_correo = request.form.get('nuevo_correo')
                nuevo_contacto = request.form.get('nuevo_contacto')
                nuevo_telefono_contacto = request.form.get('nuevo_telefono_contacto')
                
                cursor.execute("""INSERT INTO clientes (
                        razon_social, nit_cc, tipo_cliente, ciudad, direccion,
                        telefono, correo, contacto, telefono_contacto
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    nueva_razon_social, nuevo_nit_cc, nuevo_tipo_cliente, nueva_ciudad,
                    nueva_direccion, nuevo_telefono, nuevo_correo, nuevo_contacto,
                    nuevo_telefono_contacto
                ))
                
                id_cliente = cursor.lastrowid
        else:
            id_cliente = request.form.get('id_cliente')
            if not id_cliente:
                errors.append('Debe seleccionar un cliente')
        
        # Validate order fields
        required_order_fields = {
            'nombre_pedido': 'Nombre del Pedido',
            'fecha_pedido': 'Fecha del Pedido',
            'ciudad_entrega': 'Ciudad de Entrega',
            'direccion_entrega': 'Dirección de Entrega',
            'forma_pago': 'Forma de Pago',
            'id_producto': 'Producto',
            'cantidad': 'Cantidad',
            'sale_via': 'Sale Vía'
        }
        
        for field, label in required_order_fields.items():
            if not request.form.get(field):
                errors.append(f'El campo {label} es obligatorio')
        
        # Validate transportadora if sale_via is Transportadora
        if request.form.get('sale_via') == 'Transportadora' and not request.form.get('transportadora'):
            errors.append('El campo Transportadora es obligatorio cuando Sale Vía es Transportadora')
        
        # If there are validation errors, return to form with messages
        if errors:
            for error in errors:
                flash(error, 'danger')
            
            # Reload form data
            cursor.execute("SELECT id_cliente, razon_social, tipo_cliente FROM clientes ORDER BY razon_social")
            clientes = cursor.fetchall()
            
            cursor.execute("SELECT id_linea, nombre_linea FROM lineas_producto ORDER BY nombre_linea")
            lineas_producto = cursor.fetchall()
            
            cursor.execute("""SELECT p.id_producto, p.nombre_producto, p.precio, l.nombre_linea, p.id_linea
                FROM productos p
                LEFT JOIN lineas_producto l ON p.id_linea = l.id_linea
                ORDER BY p.nombre_producto
            """)
            productos = cursor.fetchall()
            
            # Convert to dict for template
            clientes_dict = [{'id_cliente': c[0], 'razon_social': c[1], 'tipo_cliente': c[2]} for c in clientes]
            lineas_dict = [{'id_linea': l[0], 'nombre_linea': l[1]} for l in lineas_producto]
            productos_dict = [{'id_producto': p[0], 'nombre_producto': p[1], 'precio': p[2], 'nombre_linea': p[3], 'id_linea': p[4]} for p in productos]
            
            return render_template('comercial/registrar_pedido.html',
                                 nombre=session.get('nombre'),
                                 clientes=clientes_dict,
                                 lineas_producto=lineas_dict,
                                 productos=productos_dict,
                                 form_data=request.form)
        
        nombre_pedido = request.form.get('nombre_pedido')
        fecha_pedido = request.form.get('fecha_pedido')
        ciudad_entrega = request.form.get('ciudad_entrega')
        direccion_entrega = request.form.get('direccion_entrega')
        forma_pago = request.form.get('forma_pago')
        valor_total = request.form.get('valor_total', 0)
        observaciones = request.form.get('observaciones')
        
        cursor.execute("SELECT COUNT(*) as total FROM pedidos")
        total = cursor.fetchone()[0]
        numero_pedido = f"PED-{datetime.now().year}-{total + 1:04d}"
        
        estado_pago = 'Crédito' if forma_pago == 'Crédito' else 'No Pagado'
        
        cursor.execute("""INSERT INTO pedidos (
                id_cliente, id_vendedor, numero_pedido, fecha_pedido,
                ciudad_entrega, direccion_entrega, forma_pago, estado,
                estado_pago, valor_total, observaciones
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            id_cliente, session.get('user_id'), numero_pedido, fecha_pedido,
            ciudad_entrega, direccion_entrega, forma_pago, 'Programado',
            estado_pago, valor_total, observaciones
        ))
        
        id_pedido = cursor.lastrowid
        
        id_producto = request.form.get('id_producto')
        cantidad = request.form.get('cantidad', 0)
        tiro_mensaje = request.form.get('tiro_mensaje')
        retiro_mensaje = request.form.get('retiro_mensaje')
        mensajes_mezclados = request.form.get('mensajes_mezclados', 'No')
        inserto = request.form.get('inserto', 'No')
        empaque = request.form.get('empaque')
        cenefa = request.form.get('cenefa', 'No')
        observacion_detalle = request.form.get('observacion_detalle')
        
        cursor.execute("SELECT precio FROM productos WHERE id_producto = %s", (id_producto,))
        producto = cursor.fetchone()
        precio_unitario = producto[0] if producto else 0
        subtotal = float(precio_unitario) * int(cantidad)
        
        cursor.execute("""INSERT INTO detalle_pedido (
                id_pedido, id_producto, cantidad, precio_unitario, subtotal,
                tiro_mensaje, retiro_mensaje, mensajes_mezclados, inserto,
                empaque, cenefa, observacion
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            id_pedido, id_producto, cantidad, precio_unitario, subtotal,
            tiro_mensaje, retiro_mensaje, mensajes_mezclados, inserto,
            empaque, cenefa, observacion_detalle
        ))
        
        sale_via = request.form.get('sale_via')
        transportadora = request.form.get('transportadora')
        pago_flete = request.form.get('pago_flete')
        nombre_receptor = request.form.get('nombre_receptor')
        telefono_receptor = request.form.get('telefono_receptor')
        fecha_salida = request.form.get('fecha_salida')
        
        cursor.execute("""INSERT INTO envios (
                id_pedido, transportadora, sale_via, pago_flete,
                nombre_receptor, telefono_receptor, fecha_envio, estado_salida
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            id_pedido, transportadora, sale_via, pago_flete,
            nombre_receptor, telefono_receptor, fecha_salida, 'No'
        ))
        
        conn.commit()
        
        # Reload form data for new order
        cursor.execute("SELECT id_cliente, razon_social, tipo_cliente FROM clientes ORDER BY razon_social")
        clientes = cursor.fetchall()
        
        cursor.execute("SELECT id_linea, nombre_linea FROM lineas_producto ORDER BY nombre_linea")
        lineas_producto = cursor.fetchall()
        
        cursor.execute("""SELECT p.id_producto, p.nombre_producto, p.precio, l.nombre_linea, p.id_linea
            FROM productos p
            LEFT JOIN lineas_producto l ON p.id_linea = l.id_linea
            ORDER BY p.nombre_producto
        """)
        productos = cursor.fetchall()
        
        # Convert to dict for template
        clientes_dict = [{'id_cliente': c[0], 'razon_social': c[1], 'tipo_cliente': c[2]} for c in clientes]
        lineas_dict = [{'id_linea': l[0], 'nombre_linea': l[1]} for l in lineas_producto]
        productos_dict = [{'id_producto': p[0], 'nombre_producto': p[1], 'precio': p[2], 'nombre_linea': p[3], 'id_linea': p[4]} for p in productos]
        
        flash(f'Pedido {numero_pedido} registrado exitosamente', 'success')
        
        return render_template('comercial/registrar_pedido.html',
                             nombre=session.get('nombre'),
                             clientes=clientes_dict,
                             lineas_producto=lineas_dict,
                             productos=productos_dict,
                             pedido_guardado=True)
        
    except Exception as e:
        conn.rollback()
        flash(f'Error al registrar el pedido: {str(e)}', 'danger')
        
        # Reload form data
        cursor.execute("SELECT id_cliente, razon_social, tipo_cliente FROM clientes ORDER BY razon_social")
        clientes = cursor.fetchall()
        
        cursor.execute("SELECT id_linea, nombre_linea FROM lineas_producto ORDER BY nombre_linea")
        lineas_producto = cursor.fetchall()
        
        cursor.execute("""SELECT p.id_producto, p.nombre_producto, p.precio, l.nombre_linea, p.id_linea
            FROM productos p
            LEFT JOIN lineas_producto l ON p.id_linea = l.id_linea
            ORDER BY p.nombre_producto
        """)
        productos = cursor.fetchall()
        
        # Convert to dict for template
        clientes_dict = [{'id_cliente': c[0], 'razon_social': c[1], 'tipo_cliente': c[2]} for c in clientes]
        lineas_dict = [{'id_linea': l[0], 'nombre_linea': l[1]} for l in lineas_producto]
        productos_dict = [{'id_producto': p[0], 'nombre_producto': p[1], 'precio': p[2], 'nombre_linea': p[3], 'id_linea': p[4]} for p in productos]
        
        return render_template('comercial/registrar_pedido.html',
                             nombre=session.get('nombre'),
                             clientes=clientes_dict,
                             lineas_producto=lineas_dict,
                             productos=productos_dict,
                             form_data=request.form)
    finally:
        cursor.close()
        conn.close()

@bp.route('/actualizar-cliente', methods=['POST'])
def actualizar_cliente():
    if 'user_type' not in session or session['user_type'] != 'comercial':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    data = request.get_json()
    id_cliente = data.get('id')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""UPDATE clientes SET
                razon_social = %s,
                nit_cc = %s,
                tipo_cliente = %s,
                ciudad = %s,
                direccion = %s,
                telefono = %s,
                correo = %s,
                contacto = %s,
                telefono_contacto = %s
            WHERE id_cliente = %s
        """, (
            data.get('razon_social'),
            data.get('nit_cc') if data.get('nit_cc') else None,
            data.get('tipo_cliente'),
            data.get('ciudad') if data.get('ciudad') else None,
            data.get('direccion') if data.get('direccion') else None,
            data.get('telefono') if data.get('telefono') else None,
            data.get('correo') if data.get('correo') else None,
            data.get('contacto') if data.get('contacto') else None,
            data.get('telefono_contacto') if data.get('telefono_contacto') else None,
            id_cliente
        ))
        
        conn.commit()
        flash('Información guardada con éxito', 'success_detalle')
        return jsonify({'success': True, 'message': 'Cliente actualizado correctamente'})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp.route('/actualizar-pedido', methods=['POST'])
def actualizar_pedido():
    if 'user_type' not in session or session['user_type'] != 'comercial':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    data = request.get_json()
    id_pedido = data.get('id')
    numero_guia = data.get('numero_guia')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""UPDATE pedidos SET
                fecha_pedido = %s,
                estado = %s,
                estado_pago = %s,
                forma_pago = %s,
                ciudad_entrega = %s,
                direccion_entrega = %s,
                valor_total = %s
            WHERE id_pedido = %s
        """, (
            data.get('fecha_pedido') if data.get('fecha_pedido') else None,
            data.get('estado'),
            data.get('estado_pago'),
            data.get('forma_pago'),
            data.get('ciudad_entrega') if data.get('ciudad_entrega') else None,
            data.get('direccion_entrega') if data.get('direccion_entrega') else None,
            data.get('valor_total') if data.get('valor_total') else None,
            id_pedido
        ))
        
        if numero_guia is not None:
            # Check if envio exists
            cursor.execute("SELECT id_envio FROM envios WHERE id_pedido = %s", (id_pedido,))
            envio_result = cursor.fetchone()
            
            if envio_result:
                # Update existing envio
                cursor.execute("UPDATE envios SET numero_guia = %s WHERE id_pedido = %s", (numero_guia if numero_guia else None, id_pedido))
                
                # If numero_guia is provided and not empty, set estado to Enviado
                if numero_guia and numero_guia.strip():
                    cursor.execute("UPDATE pedidos SET estado = 'Enviado' WHERE id_pedido = %s", (id_pedido,))
            else:
                # Create new envio if it doesn't exist and numero_guia is provided
                if numero_guia and numero_guia.strip():
                    cursor.execute("INSERT INTO envios (id_pedido, numero_guia) VALUES (%s, %s)", (id_pedido, numero_guia))
                    cursor.execute("UPDATE pedidos SET estado = 'Enviado' WHERE id_pedido = %s", (id_pedido,))
        
        conn.commit()
        flash('Información guardada con éxito', 'success_detalle')
        return jsonify({'success': True, 'message': 'Pedido actualizado correctamente'})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp.route('/actualizar-envio', methods=['POST'])
def actualizar_envio():
    if 'user_type' not in session or session['user_type'] != 'comercial':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    data = request.get_json()
    id_envio = data.get('id')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""UPDATE envios SET
                sale_via = %s,
                transportadora = %s,
                numero_guia = %s,
                pago_flete = %s,
                nombre_receptor = %s,
                telefono_receptor = %s,
                fecha_envio = %s,
                estado_salida = %s
            WHERE id_envio = %s
        """, (
            data.get('sale_via') if data.get('sale_via') else None,
            data.get('transportadora') if data.get('transportadora') else None,
            data.get('numero_guia') if data.get('numero_guia') else None,
            data.get('pago_flete') if data.get('pago_flete') else None,
            data.get('nombre_receptor') if data.get('nombre_receptor') else None,
            data.get('telefono_receptor') if data.get('telefono_receptor') else None,
            data.get('fecha_envio') if data.get('fecha_envio') else None,
            data.get('estado_salida') if data.get('estado_salida') else None,
            id_envio
        ))
        
        conn.commit()
        flash('Información guardada con éxito', 'success_detalle')
        return jsonify({'success': True, 'message': 'Envío actualizado correctamente'})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp.route('/actualizar-estado', methods=['POST'])
def actualizar_estado():
    if 'user_type' not in session or session['user_type'] != 'comercial':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    data = request.get_json()
    id_pedido = data.get('id_pedido')
    nuevo_estado = data.get('estado')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""UPDATE pedidos 
                SET estado = %s 
                WHERE id_pedido = %s
            """, (nuevo_estado, id_pedido))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Estado actualizado correctamente'})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp.route('/actualizar-estado-pago', methods=['POST'])
def actualizar_estado_pago():
    if 'user_type' not in session or session['user_type'] != 'comercial':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    data = request.get_json()
    id_pedido = data.get('id_pedido')
    nuevo_estado_pago = data.get('estado_pago')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""UPDATE pedidos 
                SET estado_pago = %s 
                WHERE id_pedido = %s
            """, (nuevo_estado_pago, id_pedido))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Estado de pago actualizado correctamente'})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp.route('/archivados')
def ver_pedidos_archivados_comercial():
    if 'user_type' not in session or session['user_type'] != 'comercial':
        flash('Acceso denegado', 'danger')
        return redirect(url_for('auth.login'))

    sort_by = request.args.get('sort_by', 'fecha')
    order = request.args.get('order', 'desc')
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT p.id_pedido, p.numero_pedido, p.fecha_pedido, p.estado, 
               p.estado_pago, p.forma_pago, p.valor_total, c.razon_social, 
               p.ciudad_entrega 
        FROM pedidos p 
        JOIN clientes c ON p.id_cliente = c.id_cliente
        WHERE p.archivado = TRUE
    """
    
    params = []
    
    if fecha_desde:
        query += " AND p.fecha_pedido >= %s"
        params.append(fecha_desde)
    
    if fecha_hasta:
        query += " AND p.fecha_pedido <= %s"
        params.append(fecha_hasta)
    
    if sort_by == 'cliente':
        query += f" ORDER BY c.razon_social {order.upper()}"
    else:
        query += f" ORDER BY p.fecha_pedido {order.upper()}"
    
    cursor.execute(query, params)
    pedidos = cursor.fetchall()
    
    if fecha_desde or fecha_hasta or request.args.get('sort_by') or request.args.get('order'):
        flash('Filtro aplicado con éxito', 'success_archivados')
    
    cursor.close()
    conn.close()

    return render_template('comercial/ver_pedidos_archivados.html', 
                         pedidos=pedidos,
                         sort_by=sort_by,
                         order=order,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta)

@bp.route('/pedidos-enviados')
def ver_pedidos_enviados():
    # Verificar que el usuario sea comercial
    if 'user_type' not in session or session['user_type'] != 'comercial':
        flash('Acceso denegado', 'danger')
        return redirect(url_for('auth.login'))
    
    sort_by = request.args.get('sort_by', 'fecha')
    order = request.args.get('order', 'desc')
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        query = """
            SELECT 
                p.id_pedido,
                p.numero_pedido,
                p.fecha_pedido,
                p.estado,
                p.estado_pago,
                p.valor_total,
                p.forma_pago,
                c.razon_social,
                c.ciudad as ciudad_cliente,
                p.ciudad_entrega,
                e.numero_guia,
                e.transportadora,
                e.fecha_envio
            FROM pedidos p
            INNER JOIN clientes c ON p.id_cliente = c.id_cliente
            LEFT JOIN envios e ON p.id_pedido = e.id_pedido
            WHERE p.estado = 'Enviado' AND e.numero_guia IS NOT NULL
        """
        
        params = []
        
        if fecha_desde:
            query += " AND p.fecha_pedido >= %s"
            params.append(fecha_desde)
        
        if fecha_hasta:
            query += " AND p.fecha_pedido <= %s"
            params.append(fecha_hasta)
        
        if sort_by == 'cliente':
            query += f" ORDER BY c.razon_social {order.upper()}"
        else:
            query += f" ORDER BY p.fecha_pedido {order.upper()}"
        
        cursor.execute(query, params)
        pedidos = cursor.fetchall()
        
        if fecha_desde or fecha_hasta or request.args.get('sort_by') or request.args.get('order'):
            flash('Filtro aplicado con éxito', 'success_enviados')
        
    except Exception as e:
        flash(f'Error al cargar pedidos enviados: {str(e)}', 'danger')
        pedidos = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('comercial/ver_pedidos_enviados.html',
                         nombre=session.get('nombre'),
                         pedidos=pedidos,
                         sort_by=sort_by,
                         order=order,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta)
