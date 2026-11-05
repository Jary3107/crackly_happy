import os
from flask import Blueprint, render_template, redirect, url_for, flash, session, request, jsonify, send_file, make_response
from database.db import get_connection
from fpdf import FPDF
from io import BytesIO
from weasyprint import HTML
import pdfkit
import smtplib
from flask_mail import Message
from extensions import mail

def get_pdfkit_config():
    """
    Busca la configuración de wkhtmltopdf.
    1. Intenta la configuración automática (si está en el PATH).
    2. Busca en rutas comunes de Windows.
    """
    try:
        # 1. Intenta la configuración automática
        return pdfkit.configuration()
    except OSError:
        # 2. Busca en rutas comunes si falla la automática
        common_paths = [
            r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
            r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe"
        ]
        for path in common_paths:
            if os.path.exists(path):
                return pdfkit.configuration(wkhtmltopdf=path)
    # Si no se encuentra en ninguna parte, lanzará un error en el momento de uso.
    raise IOError("wkhtmltopdf no se encontró. Por favor, instálalo y/o añádelo al PATH del sistema.")

# Definir el blueprint para las rutas de facturación
bp = Blueprint('facturacion', __name__, url_prefix='/facturacion')

# Ruta del dashboard de facturación
@bp.route('/dashboard')
def dashboard():
    # Verificar que el usuario sea del área de facturación
    if 'user_type' not in session or session['user_type'] != 'facturacion':
        flash('Acceso denegado', 'danger')
        return redirect(url_for('auth.login'))
    
    # Renderizar el dashboard de facturación, pasando el nombre y el rol desde la sesión
    return render_template('facturacion/dashboard.html', 
                         nombre=session.get('nombre'), 
                         rol='Facturación')

@bp.route('/pagados')
def ver_pedidos_pagados():
    if 'user_type' not in session or session['user_type'] != 'facturacion':
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
                p.ciudad_entrega
            FROM pedidos p
            INNER JOIN clientes c ON p.id_cliente = c.id_cliente
            WHERE p.estado_pago = 'Pagado'
            AND (p.archivado IS NULL OR p.archivado = 0)

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
    
    return render_template('facturacion/ver_pedidos_pagados_facturacion.html',
                         nombre=session.get('nombre'),
                         pedidos=pedidos,
                         sort_by=sort_by,
                         order=order,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta)

@bp.route('/pedidos')
def ver_pedidos():
    # Verificar que el usuario sea del área de facturación
    if 'user_type' not in session or session['user_type'] != 'facturacion':
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
    
    return render_template('facturacion/ver_pedidos_facturacion.html',
                         nombre=session.get('nombre'),
                         pedidos=pedidos,
                         sort_by=sort_by,
                         order=order,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta,
                         filtro_estado=filtro_estado)

@bp.route('/pedido/<int:id_pedido>')
def detalle_pedido(id_pedido):
    # Verificar que el usuario sea del área de facturación
    if 'user_type' not in session or session['user_type'] != 'facturacion':
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
            return redirect(url_for('facturacion.ver_pedidos'))
        
        # Obtener detalle del pedido
        cursor.execute("""SELECT dp.*, pr.nombre_producto, lp.nombre_linea FROM detalle_pedido dp INNER JOIN productos pr ON dp.id_producto = pr.id_producto LEFT JOIN lineas_producto lp ON pr.id_linea = lp.id_linea WHERE dp.id_pedido = %s""", (id_pedido,))
        detalle = cursor.fetchall()
        
        # Obtener información de envío
        cursor.execute("""SELECT * FROM envios WHERE id_pedido = %s""", (id_pedido,))
        envio = cursor.fetchone()
        
    except Exception as e:
        flash(f'Error al cargar el pedido: {str(e)}', 'danger')
        return redirect(url_for('facturacion.ver_pedidos'))
    finally:
        cursor.close()
        conn.close()
    
    return render_template('facturacion/detalle_pedido_facturacion.html',
                         nombre=session.get('nombre'),
                         pedido=pedido,
                         detalle=detalle,
                         envio=envio,
                         from_page=from_page)

@bp.route('/actualizar-cliente', methods=['POST'])
def actualizar_cliente():
    if 'user_type' not in session or session['user_type'] != 'facturacion':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    data = request.get_json()
    id_cliente = data.get('id')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""UPDATE clientes SET razon_social = %s, nit_cc = %s, tipo_cliente = %s, ciudad = %s, direccion = %s, telefono = %s, correo = %s, contacto = %s, telefono_contacto = %s WHERE id_cliente = %s""", (
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
    if 'user_type' not in session or session['user_type'] != 'facturacion':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    data = request.get_json()
    id_pedido = data.get('id')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""UPDATE pedidos SET fecha_pedido = %s, estado = %s, estado_pago = %s, forma_pago = %s, ciudad_entrega = %s, direccion_entrega = %s, valor_total = %s WHERE id_pedido = %s""", (
            data.get('fecha_pedido') if data.get('fecha_pedido') else None,
            data.get('estado'),
            data.get('estado_pago'),
            data.get('forma_pago'),
            data.get('ciudad_entrega') if data.get('ciudad_entrega') else None,
            data.get('direccion_entrega') if data.get('direccion_entrega') else None,
            data.get('valor_total') if data.get('valor_total') else None,
            id_pedido
        ))
        
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
    if 'user_type' not in session or session['user_type'] != 'facturacion':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    data = request.get_json()
    id_envio = data.get('id')
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""UPDATE envios SET sale_via = %s, transportadora = %s, numero_guia = %s, pago_flete = %s, nombre_receptor = %s, telefono_receptor = %s, fecha_envio = %s, estado_salida = %s WHERE id_envio = %s""", (
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
    if 'user_type' not in session or session['user_type'] != 'facturacion':
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
    if 'user_type' not in session or session['user_type'] != 'facturacion':
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

# generar factura
@bp.route('/factura/generar/<int:id_pedido>')
def generar_factura(id_pedido):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # --- Obtener encabezado del pedido --- 
    cursor.execute(""" 
        SELECT p.*, c.razon_social, c.correo 
        FROM pedidos p 
        INNER JOIN clientes c ON p.id_cliente = c.id_cliente 
        WHERE p.id_pedido = %s 
    """, (id_pedido,))
    pedido = cursor.fetchone()

    # --- Obtener detalle del pedido --- 
    cursor.execute(""" 
        SELECT dp.*, pr.nombre_producto 
        FROM detalle_pedido dp 
        INNER JOIN productos pr ON dp.id_producto = pr.id_producto 
        WHERE dp.id_pedido = %s 
    """, (id_pedido,))
    detalle = cursor.fetchall()

    cursor.close()
    conn.close()

    # --- Renderizar la plantilla --- 
    rendered = render_template('facturacion/factura.html', pedido=pedido, detalle=detalle)

    # --- Crear carpeta destino si no existe --- 
    output_folder = os.path.join(os.getcwd(), 'static2', 'facturas')
    os.makedirs(output_folder, exist_ok=True)

    pdf_path = os.path.join(output_folder, f'factura_{pedido["numero_pedido"]}.pdf')

    config = get_pdfkit_config() # Obtiene la configuración correcta

    # --- Generar el PDF --- 
    pdfkit.from_string(rendered, pdf_path, configuration=config, options={'enable-local-file-access': ''})

    # --- Enviar el archivo generado --- 
    response = send_file(pdf_path, as_attachment=True)
    return response

# envia factura
@bp.route('/factura/enviar/<int:pedido_id>')
def enviar_factura(pedido_id):
    conexion = get_connection()
    cursor = conexion.cursor(dictionary=True)

    # Obtener pedido y cliente asociados
    cursor.execute(""" 
        SELECT 
            p.id_pedido,
            p.numero_pedido,
            c.razon_social AS nombre,
            c.correo AS correo,
            p.valor_total,
            p.fecha_pedido,
            p.ciudad_entrega,
            p.direccion_entrega
        FROM pedidos p
        JOIN clientes c ON p.id_cliente = c.id_cliente
        WHERE p.id_pedido = %s
    """, (pedido_id,))
    pedido = cursor.fetchone()

    if not pedido:
        flash("Pedido no encontrado.", "danger")
        return redirect(url_for('facturacion.ver_pedidos_pagados'))

    if not pedido['correo']:
        flash("El cliente no tiene correo registrado.", "warning")
        return redirect(url_for('facturacion.ver_pedidos_pagados'))

    # Crear el mensaje
    msg = Message(
    subject=f"Factura del pedido #{pedido['numero_pedido']}",
    sender="cracklyhappy@gmail.com", 
    recipients=[pedido['correo']]
)
    msg.body = f"""
    Hola {pedido['nombre']},

    Te enviamos la factura correspondiente al pedido #{pedido['numero_pedido']}.
    Valor total: ${pedido['valor_total']:,.2f}

    Gracias por tu compra.
    """

    # Enviar el correo
    try:
        mail.send(msg)
        flash(f"Factura enviada correctamente a {pedido['correo']}.", "success")
    except Exception as e:
        flash(f"Error al enviar el correo: {str(e)}", "danger")

    conexion.close()
    return redirect(url_for('facturacion.ver_pedidos_pagados'))

@bp.route('/factura/archivar/<int:id_pedido>', methods=['POST'])
def archivar_desde_factura(id_pedido):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE pedidos SET archivado = 1 WHERE id_pedido = %s", (id_pedido,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Pedido archivado correctamente.", "success_pagados")
    return redirect(url_for('facturacion.ver_pedidos_pagados'))

@bp.route('/archivados')
def ver_pedidos_archivados():
    if 'user_type' not in session or session['user_type'] != 'facturacion':
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

    return render_template('facturacion/ver_pedidos_archivados.html', 
                         pedidos=pedidos,
                         sort_by=sort_by,
                         order=order,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta)
