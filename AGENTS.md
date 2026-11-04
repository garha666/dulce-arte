# AGENTS.md — Dulce Arte (EVA 3 Backend)

Sistema de trazabilidad y pedidos para una pastelería artesanal: cotización de pedidos
personalizados, tablero Kanban de cocina, descuento de insumos por receta (BOM) y despacho
con confirmación de entrega. Proyecto individual de la asignatura Desarrollo Backend.

## Stack y estructura
- Django 5.2 + Django REST Framework + PostgreSQL + templates HTML/CSS/JS (sin frameworks JS).
- `drf/` proyecto (settings por `.env`, `urls.py` raíz). `api/` única app: `models.py`,
  `admin.py`, `serializers.py`, `views.py`, `permissions.py`, `urls.py`.
- `templates/` páginas HTML; `static/` CSS y JS; `media/` archivos subidos.
- `docs/` constitución y modelo de datos; `specs/` especificaciones SDD; `deploy/` archivos de EC2.

## Comandos
- Activar entorno: `.\env\Scripts\activate`
- Servidor: `python manage.py runserver`
- Migraciones: `python manage.py makemigrations` y `python manage.py migrate`
- Datos de prueba: `python seed_data.py`
- Verificación: `python manage.py check` y `python smoke_test.py`
- PostgreSQL local: `docker compose up -d`

## Convenciones
- Código, nombres de modelos y variables en inglés técnico estándar de Django; textos de
  interfaz, mensajes y documentación en español.
- Modelos en singular (`Pedido`, `Insumo`), `related_name` en plural.
- Lógica de negocio en el modelo (`Pedido.cambiar_estado`, `Pedido.descontar_insumos`),
  no en las vistas.
- Templates con `{% extends "base.html" %}`; estilos en `static/css/estilos.css`.

## Reglas de dominio (fáciles de romper)
- El estado del pedido **solo** cambia por `Pedido.cambiar_estado`; valida `TRANSICIONES`.
- El descuento de insumos ocurre **una sola vez** (bandera `insumos_descontados`) al pasar
  a `preparacion`, y debe ser atómico (`transaction.atomic`).
- Un despacho no se confirma sin firma o comprobante (`Despacho.clean`).
- Las fechas de entrega usan `America/Santiago`; nunca comparar con UTC.

## Forma de trabajar
- Antes de cambios grandes, leer `docs/constitution.md` y la spec activa en `specs/`.
- Cambios pequeños y enfocados; no reescribir lo que ya funciona.
- Al terminar, resumir qué se cambió y actualizar `MEMORY.md`.

## Límites
- ✅ Siempre: validar con `manage.py check` y `smoke_test.py`; mantener datos de prueba.
- ⚠ Pregunta antes: agregar dependencias, cambiar modelos ya migrados, tocar `deploy/`.
- 🚫 Nunca: subir `.env`, credenciales o `db.sqlite3`; dejar el repo sin `README.md`.

## Verificación
- `python manage.py check` sin errores.
- `python smoke_test.py`: todas las páginas 200, cambio de estado 200 y transición inválida 400.
