# Proyecto Crackly Happy

Este es el archivo README para el proyecto de la aplicación web de Crackly Happy.

## Documentación del Chatbot

El chatbot del dashboard de cliente está impulsado por la API de Google Gemini y está diseñado para responder preguntas de los usuarios en lenguaje natural.

### Capacidades del Chatbot

El chatbot puede responder a una variedad de preguntas basadas en dos fuentes de información:

1.  **Información Dinámica de la Base de Datos:**
    *   Preguntas sobre las **líneas de productos** disponibles.
    *   Consultas sobre **productos específicos**, sus precios y descripciones.
    *   Preguntas sobre cuál es el producto más económico, el más caro, etc.

2.  **Información General (Estática):**
    *   **Ubicación:** "¿Dónde están ubicados?"
    *   **Horarios:** "¿Cuál es su horario de atención?"
    *   **Envíos:** "¿Hacen envíos a otras ciudades?"
    *   **Métodos de pago:** "¿Qué métodos de pago aceptan?"
    *   **Personalizaciones:** "¿Ofrecen galletas personalizadas?"

### Acciones Especiales

*   **Ver Catálogo:** Si un usuario pregunta por el "catálogo" o los "productos", el chatbot responderá con un botón que redirige al usuario a la página del catálogo de productos. Esto se logra mediante la detección de la palabra clave `[ACTION:VIEW_CATALOG]` en la respuesta de la IA.