# prompts_ia.md — Registro de uso de IA

Evidencia del apoyo de herramientas de IA durante el desarrollo de la Evaluación N°3.
Formato: qué se pidió, qué se obtuvo, qué se aceptó/rechazó y qué archivo quedó afectado.

Herramienta utilizada: **OpenCode** (agente de código) con modelo de lenguaje.
Criterio de uso: la IA propone, el alumno revisa, prueba y decide.

## Registro

| # | Etapa | Prompt entregado a la IA | Resultado obtenido | Decisión del alumno | Archivos |
|---|---|---|---|---|---|
| 1 | Análisis del caso | "Lee los documentos de la evaluación (EVA_3, proyectos, temas) e identifica el proyecto asignado y los requisitos técnicos." | Resumen del Proyecto 3 (Dulce Arte) con las 4 funcionalidades y la rúbrica. | Aceptado: se usó como checklist de la rúbrica. | — |
| 2 | Diseño de datos | "Propón el modelo de datos del caso en 3FN, separando el BOM en una tabla intermedia y explicando por qué no se repiten datos." | Tablas `Insumo`, `CategoriaInsumo`, `Producto`, `RecetaInsumo`, `Pedido`, `PedidoDetalle`, `HistorialEstado`, `MovimientoInsumo`, `Despacho`. | Aceptado con cambio: se agregó `insumos_descontados` para evitar doble descuento. | `api/models.py`, `docs/modelo_datos.md` |
| 3 | Reglas del Kanban | "Implementa el flujo de estados con transiciones válidas y error si el cambio no está permitido." | Método `Pedido.cambiar_estado` + diccionario `TRANSICIONES` + registro en `HistorialEstado`. | Aceptado; se agregó la devolución de "Control de calidad" a "En preparación". | `api/models.py`, `api/views.py` |
| 4 | Descuento de insumos (BOM) | "Al pasar a preparación descuenta los insumos de la receta de forma atómica y rechaza la operación si falta stock." | `descontar_insumos` con `select_for_update`, validación de faltantes y `MovimientoInsumo`. | Aceptado; se agregó la bandera para que el descuento ocurra una sola vez. | `api/models.py` |
| 5 | Admin personalizado | "Personaliza el Admin de todos los modelos con list_display, list_filter, search_fields e inlines para el detalle y el BOM." | `ModelAdmin` por modelo, inlines, cabecera `site_header` y acción masiva. | Aceptado; se ajustaron campos de solo lectura de montos. | `api/admin.py` |
| 6 | API REST | "Crea los serializers y ViewSets con detalles anidados y una acción cambiar_estado que responda 400 si falla la regla." | Serializers anidados y ViewSets con `@action`. | Aceptado; se limitó la escritura de catálogos a administradores. | `api/serializers.py`, `api/views.py`, `api/permissions.py` |
| 7 | Frontend | "Genera templates responsivos con la paleta de la pastelería y un tablero Kanban que consuma la API con fetch y X-CSRFToken." | `base.html`, `home`, `kanban`, `pedidos`, `inventario`, `despachos`, `contacto` + CSS y JS. | Aceptado; se cambió el Kanban a render del servidor con acciones asíncronas. | `templates/`, `static/` |
| 8 | Datos de prueba y verificación | "Crea un seed idempotente y una prueba de humo que valide páginas, transición válida e inválida." | `seed_data.py` y `smoke_test.py`. | Aceptado; se corrigió `ALLOWED_HOSTS` para el cliente de pruebas. | `seed_data.py`, `smoke_test.py` |
| 9 | Despliegue | "Adapta la receta de EC2 (Gunicorn + Nginx) para incluir PostgreSQL, estáticos y permisos del socket." | `deploy/gunicorn.service`, `deploy/nginx.conf`, guía paso a paso. | Pendiente de ejecutar en la instancia. | `deploy/` |

## Qué se rechazó y por qué
- **Vista única tipo SPA con React**: descartada porque la receta del ramo pide templates de Django.
- **Descontar insumos en el serializer**: descartado para no duplicar la regla en la API y en las vistas HTML.
- **Guardar el estado como texto libre**: descartado; se usan `choices` y un historial de eventos.

## Verificación humana
Cada cambio se probó con `python manage.py check` y `python smoke_test.py`.
Las credenciales del `.env` no se comparten con la IA ni se suben al repositorio.
