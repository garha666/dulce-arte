# MEMORY.md — Dulce Arte

Memoria del proyecto entre sesiones. Máximo ~50 líneas.

## Estado actual
- Proyecto Django `drf` + app `api`; modelos en 3FN (insumos, BOM, pedidos, historial,
  movimientos, despachos y perfiles).
- Admin personalizado y API DRF con acciones `cambiar_estado` y `descontar_insumos`.
- Rediseño por roles: landing pública, paneles por rol, `api/roles.py` y
  `api/context_processors.py`; menús y accesos centralizados.
- La API aplica los mismos roles que las páginas: ventas no descuenta insumos ni mueve el
  Kanban; cocina/calidad no crean ni borran pedidos o despachos; despacho gestiona sus rutas.
- Flujo de despacho cerrado: solo pedidos `listo`, receptor y evidencia obligatorios, sin
  doble confirmación, transición atómica a `entregado` y bloqueo de `entregado` sin despacho
  confirmado.
- Pedidos con `insumos_descontados=True` no se editan ni eliminan por la API.
- El listado JS escapa `cliente_nombre` y el código antes de insertarlos en `innerHTML`.
- **24 pruebas automáticas** en `api/tests.py` (Kanban, BOM, permisos, despacho, bloqueo
  post-BOM y escape del frontend): todas OK.
- Verificado: `manage.py check` OK; `smoke_test.py` exige un pedido `recibido` y valida
  páginas 200, descuento de stock y transición inválida 400.
- PostgreSQL 16 verificado en Docker (`localhost:5433`, 10 insumos, BOM y pedidos de prueba).
- Repositorio git publicado en <https://github.com/garha666/dulce-arte> (rama `master`).

## Decisiones (y por qué)
- Una sola app `api`: estructura de la receta del ramo y defensa más simple.
- Lógica de negocio en el modelo (`cambiar_estado`, `descontar_insumos`, `Despacho.clean`);
  las vistas solo orquestan.
- Permisos compartidos en `roles.py` + `permissions.py` para que HTML y API no diverjan.
- `insumos_descontados` evita el doble descuento; el despacho confirmado es la única evidencia
  válida para pasar a `entregado`.
- SQLite solo para pruebas rápidas; la entrega usa PostgreSQL en EC2 (Docker local en 5433).

## Aprendizajes y errores a evitar
- `ALLOWED_HOSTS` debe incluir la IP elástica de la EC2, o Django responde 400.
- `STATIC_ROOT` + `collectstatic` son obligatorios para que Nginx sirva Admin y DRF.
- Ocultar un botón no protege una regla: la API también debe validar permisos y estado.
- El seed de demo crea claves conocidas: `instalar.sh` ya no lo ejecuta por defecto
  (`SEED_DEMO_DATA=true` es explícito) y genera `SECRET_KEY` y clave de PostgreSQL aleatorias.

## Pendientes
- Completar la IP pública en `README.md` y verificar el despliegue en EC2.
- Configurar HTTPS en Nginx y activar `DJANGO_SECURE_COOKIES=True` en la instancia.
