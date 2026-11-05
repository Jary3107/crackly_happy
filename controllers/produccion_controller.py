from flask import Blueprint, render_template, redirect, url_for, flash, session, request, jsonify
from database.db import get_connection

# Definir el blueprint para las rutas de producción
bp = Blueprint('produccion', __name__, url_prefix='/produccion')

# Ruta del dashboard de producción
@bp.route('/dashboard')
def dashboard():
    # Verificar que el usuario sea del área de producción
    if 'user_type' not in session or session['user_type'] != 'produccion':
        flash('Acceso denegado', 'danger')
        return redirect(url_for('auth.login'))
    
    # Renderizar el dashboard de producción, pasando el nombre y el rol desde la sesión
    return render_template('produccion/dashboard.html', 
                         nombre=session.get('nombre'), 
                         rol='Producción')

@bp.route('/pedidos-pagados')
def ver_pedidos_pagados():
    # Verificar que el usuario sea del área de producción
    if 'user_type' not in session or session['user_type'] != 'produccion':
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
        flash(f'Error al cargar pedidos: {str(e)}', 'danger')
        pedidos = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('produccion/ver_pedidos_pagados_produccion.html',
                         nombre=session.get('nombre'),
                         pedidos=pedidos,
                         sort_by=sort_by,
                         order=order,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta)

@bp.route('/pedidos')
def ver_pedidos():
    # Verificar que el usuario sea del área de producción
    if 'user_type' not in session or session['user_type'] != 'produccion':
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
                p.forma_pago,
                p.valor_total,
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
    
    return render_template('produccion/ver_pedidos_produccion.html',
                         nombre=session.get('nombre'),
                         pedidos=pedidos,
                         sort_by=sort_by,
                         order=order,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta,
                         filtro_estado=filtro_estado)

@bp.route('/pedido/<int:id_pedido>')
def detalle_pedido(id_pedido):
    # Verificar que el usuario sea del área de producción
    if 'user_type' not in session or session['user_type'] != 'produccion':
        flash('Acceso denegado', 'danger')
        return redirect(url_for('auth.login'))
    
    from_page = request.args.get('from', '')
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Obtener información del pedido
        cursor.execute("""SELECT p.*, c.razon_social, c.nit_cc, c.tipo_cliente, c.direccion as direccion_cliente, c.ciudad as ciudad_cliente, c.telefono, c.correo, c.contacto, c.telefono_contacto, u.nombre as nombre_vendedor FROM pedidos p INNER JOIN clientes c ON p.id_cliente = c.id_cliente LEFT JOIN usuarios u ON p.id_vendedor = u.id_usuario WHERE p.id_pedido = %s""", (id_pedido,))
        pedido = cursor.fetchone()
        
        if not pedido:
            flash('Pedido no encontrado', 'warning')
            return redirect(url_for('produccion.ver_pedidos'))
        
        # Obtener detalle del pedido
        cursor.execute("""SELECT dp.*, pr.nombre_producto, lp.nombre_linea FROM detalle_pedido dp INNER JOIN productos pr ON dp.id_producto = pr.id_producto LEFT JOIN lineas_producto lp ON pr.id_linea = lp.id_linea WHERE dp.id_pedido = %s""", (id_pedido,))
        detalle = cursor.fetchall()
        
        # Obtener información de envío
        cursor.execute("""SELECT * FROM envios WHERE id_pedido = %s""", (id_pedido,))
        envio = cursor.fetchone()
        
    except Exception as e:
        flash(f'Error al cargar el pedido: {str(e)}', 'danger')
        return redirect(url_for('produccion.ver_pedidos'))
    finally:
        cursor.close()
        conn.close()
    
    return render_template('produccion/detalle_pedido_produccion.html',
                         nombre=session.get('nombre'),
                         pedido=pedido,
                         detalle=detalle,
                         envio=envio,
                         from_page=from_page)

@bp.route('/actualizar-cliente', methods=['POST'])
def actualizar_cliente():
    if 'user_type' not in session or session['user_type'] != 'produccion':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    data = request.get_json()
    id_cliente = data.get('id')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""UPDATE clientes SET razon_social = %s, nit_cc = %s, tipo_cliente = %s, ciudad = %s, direccion = %s, telefono = %s, correo = %s, contacto = %s, telefono_contacto = %s WHERE id_cliente = %s""", (data.get('razon_social'), data.get('nit_cc') if data.get('nit_cc') else None, data.get('tipo_cliente'), data.get('ciudad') if data.get('ciudad') else None, data.get('direccion') if data.get('direccion') else None, data.get('telefono') if data.get('telefono') else None, data.get('correo') if data.get('correo') else None, data.get('contacto') if data.get('contacto') else None, data.get('telefono_contacto') if data.get('telefono_contacto') else None, id_cliente))
        
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
    if 'user_type' not in session or session['user_type'] != 'produccion':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    data = request.get_json()
    id_pedido = data.get('id')
    numero_guia = data.get('numero_guia')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""UPDATE pedidos SET fecha_pedido = %s, estado = %s, estado_pago = %s, forma_pago = %s, ciudad_entrega = %s, direccion_entrega = %s, valor_total = %s WHERE id_pedido = %s""", (data.get('fecha_pedido') if data.get('fecha_pedido') else None, data.get('estado'), data.get('estado_pago'), data.get('forma_pago'), data.get('ciudad_entrega') if data.get('ciudad_entrega') else None, data.get('direccion_entrega') if data.get('direccion_entrega') else None, data.get('valor_total') if data.get('valor_total') else None, id_pedido))
        
        if numero_guia is not None:
            # Check if envio exists
            cursor.execute("SELECT id_envio FROM envios WHERE id_pedido = %s", (id_pedido,))
            envio_result = cursor.fetchone()
            
            if envio_result:
                # Update existing envio
                cursor.execute("UPDATE envios SET numero_guia = %s WHERE id_pedido = %s", (numero_guia if numero_guia else None, id_pedido))
                
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
    if 'user_type' not in session or session['user_type'] != 'produccion':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    data = request.get_json()
    id_envio = data.get('id')
    numero_guia = data.get('numero_guia')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""UPDATE envios SET sale_via = %s, transportadora = %s, numero_guia = %s, pago_flete = %s, nombre_receptor = %s, telefono_receptor = %s, fecha_envio = %s, estado_salida = %s WHERE id_envio = %s""", (data.get('sale_via') if data.get('sale_via') else None, data.get('transportadora') if data.get('transportadora') else None, data.get('numero_guia') if data.get('numero_guia') else None, data.get('pago_flete') if data.get('pago_flete') else None, data.get('nombre_receptor') if data.get('nombre_receptor') else None, data.get('telefono_receptor') if data.get('telefono_receptor') else None, data.get('fecha_envio') if data.get('fecha_envio') else None, data.get('estado_salida') if data.get('estado_salida') else None, id_envio))
        
        if numero_guia:
            cursor.execute("SELECT id_pedido FROM envios WHERE id_envio = %s", (id_envio,))
            result = cursor.fetchone()
            if result:
                id_pedido = result[0]
                cursor.execute("UPDATE pedidos SET estado = 'Enviado' WHERE id_pedido = %s", (id_pedido,))
        
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
    if 'user_type' not in session or session['user_type'] != 'produccion':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    data = request.get_json()
    id_pedido = data.get('id_pedido')
    nuevo_estado = data.get('estado')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""UPDATE pedidos SET estado = %s WHERE id_pedido = %s""", (nuevo_estado, id_pedido))
        
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
    if 'user_type' not in session or session['user_type'] != 'produccion':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    data = request.get_json()
    id_pedido = data.get('id_pedido')
    nuevo_estado_pago = data.get('estado_pago')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""UPDATE pedidos SET estado_pago = %s WHERE id_pedido = %s""", (nuevo_estado_pago, id_pedido))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Estado de pago actualizado correctamente'})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@bp.route('/archivados')
def ver_pedidos_archivados_produccion():
    if 'user_type' not in session or session['user_type'] != 'produccion':
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

    return render_template('produccion/ver_pedidos_archivados.html', 
                         pedidos=pedidos,
                         sort_by=sort_by,
                         order=order,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta)

@bp.route('/pedidos-enviados')
def ver_pedidos_enviados():
    # Verificar que el usuario sea del área de producción
    if 'user_type' not in session or session['user_type'] != 'produccion':
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
    
    return render_template('produccion/ver_pedidos_enviados.html',
                         nombre=session.get('nombre'),
                         pedidos=pedidos,
                         sort_by=sort_by,
                         order=order,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta)
