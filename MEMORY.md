# MEMORY.md — Dulce Arte

Memoria del proyecto entre sesiones. Máximo ~50 líneas.

## Estado actual
- Proyecto Django `drf` + app `api` creado según receta del ramo.
- Modelos completos en 3FN: insumos, categorías, productos, BOM (`RecetaInsumo`),
  clientes, pedidos, detalle, historial de estados, movimientos de insumos, despachos,
  perfiles de usuario y mensajes de contacto.
- Admin personalizado (cabecera, list_display, list_filter, search_fields, inlines).
- API DRF con ViewSets + acciones `cambiar_estado` y `descontar_insumos`.
- Templates: home, kanban, pedidos, inventario, despachos, detalle, login, quiénes somos,
  servicios y contacto. JS con fetch y `X-CSRFToken` para el Kanban y pedidos.
- Datos de prueba con `seed_data.py` (5 usuarios, 10 insumos, 3 productos, 4 pedidos).
- Verificado: `manage.py check` OK; `smoke_test.py` con todas las páginas en 200.
- **PostgreSQL 16 verificado** (contenedor Docker en `localhost:5433`): migraciones aplicadas,
  seed cargado (4 pedidos, 10 insumos, 18 ingredientes BOM) y `smoke_test.py` con los mismos
  resultados que en SQLite.

## Decisiones (y por qué)
- Una sola app `api`: es la estructura que pide la receta del ramo y simplifica la defensa.
- Lógica del Kanban en el modelo: evita que la API y las vistas HTML se comporten distinto.
- SQLite solo para pruebas locales rápidas; la entrega usa PostgreSQL en la instancia EC2.
- `insumos_descontados` como bandera: garantiza que el BOM se descuente una única vez.
- Docker publica Postgres en **5433** porque el puerto 5432 del equipo ya está ocupado por
  otro PostgreSQL local; en la EC2 se usa el 5432 estándar.

## Aprendizajes y errores a evitar
- `ALLOWED_HOSTS` debe incluir la IP elástica de la EC2, o Django responde 400.
- `STATIC_ROOT` + `collectstatic` son obligatorios para que Nginx sirva Admin y DRF.

## Próximos pasos
- Inicializar repositorio git, primer commit y subir a GitHub.
- Desplegar en EC2 (Gunicorn + Nginx + Postgres) y completar `README.md` con la IP pública.
- Preparar el guion de la defensa y completar `prompts_ia.md` con los prompts reales.
