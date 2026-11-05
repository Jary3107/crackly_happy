# 🥠 Crackly Happy — Sistema de Gestión y Comercio Electrónico

> *"Las galletas que conversan"* — Plataforma web integral para la comercialización, gestión de pedidos, producción y facturación de galletas de la fortuna personalizadas.

---

## 📋 Descripción del Proyecto

**Crackly Happy** es una aplicación web desarrollada en **Python (Flask)** conectada a una base de datos relacional en la nube (**MySQL / TiDB Cloud**). El sistema centraliza tanto la tienda en línea para clientes como la operación interna de la empresa a través de paneles especializados según el rol del usuario.

---

## ✨ Funcionalidades Principales por Rol

### 👤 Módulo Público y Clientes
- **Catálogo de Productos:** Visualización de productos organizados por líneas (clásicas, personalizadas, temporada, corporativas) con precios y detalles.
- **Carrito de Compras y Pedidos:** Agregado y actualización de productos, cálculo automático de totales y creación de pedidos en línea.
- **Asistente Virtual con IA (Google Gemini):** Chatbot integrado en el panel de cliente capaz de responder preguntas en lenguaje natural sobre precios, líneas de productos, envíos, horarios, métodos de pago y redirigir directamente al catálogo.
- **Gestión de Perfil e Historial:** Actualización de datos personales/empresariales y seguimiento en tiempo real del estado de los pedidos y número de guía.
- **Autenticación y Seguridad:** Registro con validación de contraseñas seguras (encriptadas con `bcrypt`) y recuperación de contraseña por correo electrónico mediante tokens temporales.

### 💼 Módulo Comercial
- **Registro de Pedidos Corporativos y Personalizados:** Creación de pedidos asociando clientes existentes o nuevos, con configuración detallada (mensajes de tiro y retiro, mensajes mezclados, insertos, empaque, cenefa y datos de envío).
- **Gestión y Seguimiento:** Consulta y filtrado de pedidos programados, pagados, enviados (con número de guía y transportadora) y archivados, con edición en línea.

### 🏭 Módulo de Producción
- **Control de Producción:** Visualización y filtrado de pedidos programados y pagados listos para fabricación.
- **Actualización de Estados y Despacho:** Gestión del flujo de estados (`Pendiente` → `Programado` → `Producción` → `Enviado`) y asignación de guía de transporte.

### 🧾 Módulo de Facturación
- **Generación de Facturas en PDF:** Creación y descarga automática de facturas en formato PDF mediante `pdfkit` / `wkhtmltopdf`.
- **Envío por Correo Electrónico:** Envío directo de la factura al correo del cliente usando `Flask-Mail`.
- **Archivo de Pedidos:** Control de estados de pago (`No Pagado`, `Pagado`, `Crédito`) y archivado de pedidos facturados.

### 🛡️ Módulo de Administración
- **Gestión de Personal:** Panel exclusivo para el registro de cuentas internas asignando roles específicos (`Comercial`, `Produccion`, `Facturacion`, `Admin`).

---

## 🛠️ Tecnologías Utilizadas

- **Backend:** Python 3, Flask, Blueprints modulares
- **Base de Datos:** MySQL (`mysql-connector-python`) sobre TiDB Cloud con conexión segura SSL
- **Inteligencia Artificial:** API de Google Gemini (`google-generativeai`)
- **Seguridad:** Encriptación de contraseñas con `bcrypt`, sesiones seguras y tokens de recuperación
- **Correos y Reportes:** `Flask-Mail` / `smtplib` para notificaciones y `pdfkit` (`wkhtmltopdf`) / `WeasyPrint` para generación de PDF
- **Frontend:** HTML5, CSS3, Bootstrap 5, FontAwesome, JavaScript (Fetch API)

---

## 📂 Estructura del Proyecto

```text
proyectoPA/
├── app.py                      # Punto de entrada principal de la aplicación Flask
├── config.py                   # Configuración general y de servidor de correo
├── extensions.py               # Inicialización de extensiones (Flask-Mail)
├── estructuradb.text           # Script SQL con la estructura de tablas de CookieDB
├── requirements.txt            # Dependencias del proyecto
├── controllers/                # Lógica de negocio dividida por Blueprints
│   ├── admin_controller.py
│   ├── auth_controller.py
│   ├── cliente_controller.py
│   ├── comercial_controller.py
│   ├── facturacion_controller.py
│   ├── produccion_controller.py
│   └── public_controller.py
├── database/                   # Conexión a base de datos y certificados SSL
│   ├── db.py
│   ├── hashadmin.py
│   └── certs/ca.pem
├── static/                     # Recursos estáticos (imágenes, estilos, logos)
└── templates/                  # Vistas HTML organizadas por módulo
    ├── admin/
    ├── cliente/
    ├── comercial/
    ├── facturacion/
    └── produccion/
```

---

## 🚀 Instalación y Ejecución Local

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/Jary3107/crackly_happy.git
   cd crackly_happy
   ```

2. **Crear y activar el entorno virtual:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

3. **Instalar las dependencias:**
   ```powershell
   pip install -r requirements.txt
   ```
   *(Nota: Para la generación de facturas en PDF se requiere tener instalado [wkhtmltopdf](https://wkhtmltopdf.org/downloads.html) en el sistema).*

4. **Configurar variables de entorno:**
   Crear los archivos `.env`, `email.env` y `database/data.env` con las credenciales correspondientes de la base de datos MySQL, servidor SMTP y `GEMINI_API_KEY`.

5. **Ejecutar la aplicación:**
   ```powershell
   python app.py
   ```
   La aplicación estará disponible en `http://127.0.0.1:5000`.

---

## 👨‍💻 Creadores / Autores

Proyecto desarrollado por:

- **Samuel Marín**
- **Jary Preston**
- **Sebastián Salazar**

---

© Crackly Happy — Todos los derechos reservados.
