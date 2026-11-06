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
| 10 | Rediseño por roles | "Reorganiza la interfaz con landing pública, paneles distintos por rol y una navegación que muestre solo lo que cada usuario necesita, sin frameworks JS." | `templates/landing.html`, `templates/paneles/`, `api/roles.py`, `api/context_processors.py`, estilos y fuentes locales. | Aceptado; se mantuvieron los templates y la lógica existente. | `templates/`, `static/`, `api/roles.py`, `api/context_processors.py`, `drf/settings.py` |
| 11 | Endurecimiento de API y negocio | "Haz que la API respete los roles, impide crear despachos de pedidos no listos, exige evidencia y receptor, cierra el pedido al confirmar y bloquea editar/borrar después del BOM." | Permisos por rol en `api/permissions.py`, validaciones en modelo/serializer/vistas y transición atómica del despacho. | Aceptado; se agregaron pruebas para cada regla. | `api/permissions.py`, `api/views.py`, `api/models.py`, `api/serializers.py` |
| 12 | Pruebas y documentación | "Agrega pruebas de permisos, despacho, BOM y escape de HTML; actualiza README, MEMORY, spec, guion y registro de IA." | 24 pruebas en `api/tests.py`, `smoke_test.py` más estricto, documentación sincronizada y escape en `pedidos.js`. | Aceptado; la verificación final se ejecutó con `manage.py check` y `manage.py test api`. | `api/tests.py`, `smoke_test.py`, `static/js/pedidos.js`, `README.md`, `MEMORY.md`, `specs/`, `docs/` |
| 13 | Tienda real | "Convierte esto en una tienda de pastelería real: catálogo público, carrito, checkout, seguimiento y cuentas de cliente, sin frameworks JS." | `CategoriaProducto`, carrito en sesión, checkout, seguimiento por token, registro, `mis-pedidos`, templates y CSS de tienda. | Aceptado; se mantuvo el carrito en sesión y se recalculan precios desde el catálogo. | `api/models.py`, `api/carrito.py`, `api/forms.py`, `api/views.py`, `templates/`, `static/css/estilos.css` |
| 14 | Cierre de la API | "Los roles operativos no deberían poder usar la API; deja la API solo para administración y que el panel funcione sin fetch." | Permiso global `EsAdministrador`, API cerrada a ventas/cocina/calidad/despacho/cliente y panel convertido a formularios server-side. | Aceptado; se eliminaron `pedidos.js` y `kanban.js` y se agregó una prueba que prohíbe `/api/` en templates internos. | `api/permissions.py`, `api/views.py`, `api/urls.py`, `drf/settings.py`, `templates/` |
| 15 | Pagos y agenda | "Modela pagos reales, cupos, anticipación y el flujo `confirmado`/`despachado`; no permitas producir sin pago ni entregar sin evidencia." | Modelo `Pago`, `estado_pago`/`saldo` derivados, `validar_agenda` (48 h, horario y cupo), `reponer_insumos` y transiciones nuevas. | Aceptado; se corrigió el conteo de cupo para usar rango de fecha local y no UTC. | `api/models.py`, `api/migrations/0002_*.py`, `seed_data.py` |
| 16 | Pruebas y documentación de la tienda | "Actualiza pruebas, seed, smoke test, README, MEMORY, spec, glosario, ADRs y guion para la tienda y la API administrativa." | 43 pruebas, seed con cliente demo, smoke no destructivo, spec 002, `GLOSSARY.md`, 5 ADRs y documentación sincronizada. | Aceptado; la verificación final se ejecutó con `manage.py check`, `manage.py test api` y `smoke_test.py`. | `api/tests.py`, `smoke_test.py`, `seed_data.py`, `README.md`, `MEMORY.md`, `specs/002-*/`, `GLOSSARY.md`, `docs/` |

## Qué se rechazó y por qué
- **Vista única tipo SPA con React**: descartada porque la receta del ramo pide templates de Django.
- **Descontar insumos en el serializer**: descartado para no duplicar la regla en la API y en las vistas HTML.
- **Guardar el estado como texto libre**: descartado; se usan `choices` y un historial de eventos.
- **Mantener permisos por rol en la API**: descartado; el panel HTML cubre a ventas, cocina, calidad y despacho, y la API quedó solo para administración.
- **Pasarela de pago y facturación electrónica**: descartadas por alcance; el pago se registra manualmente (efectivo, transferencia o tarjeta).
- **Carrito persistente en base de datos**: descartado; el carrito en sesión permite comprar sin cuenta y el precio se lee siempre del catálogo.

## Verificación humana
Cada cambio se probó con `python manage.py check`, `python manage.py test api` y
`python smoke_test.py`. Las credenciales del `.env` no se comparten con la IA ni se suben al
repositorio; las claves de demo solo se usan en local.
