from flask import Blueprint, render_template
from database.db import get_connection

public = Blueprint('public', __name__)

@public.route('/catalogo')
def catalogo_publico():

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

    productos_por_linea = {}
    for p in rows:
        linea = p["nombre_linea"] or "Otros"
        productos_por_linea.setdefault(linea, []).append(p)

    return render_template("catalogo.html",
                           productos_por_linea=productos_por_linea,
                           publico=True)   


@public.route('/producto/<int:id>')
def producto_detalle_publico(id):
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

    # IMPORTANTE: ENVIAR publico = True
    return render_template("detalle_producto.html", producto=producto, publico=True)
