# MEMORY.md — Dulce Arte

Memoria del proyecto entre sesiones. Máximo ~50 líneas.

## Estado actual
- Django `drf` + app `api`; dominio en 3FN con insumos, BOM, pedidos, historial, movimientos,
  pagos, despachos, perfiles y cuentas de cliente.
- **Tienda completa con imágenes**: catálogo por categorías, disponibilidad desde el BOM, carrito
  en sesión, checkout, seguimiento, registro y `mis-pedidos`. Cada producto usa la foto subida en
  el Admin o una imagen demo de `static/IMAGES/productos/`.
- **Panel interno server-side**: pedidos, Kanban, inventario, pagos, despachos y retiros. Las
  acciones del Kanban se filtran por rol (`Pedido.TRANSICIONES_ROL`).
- **Equipo y roles**: `/equipo/` (solo admin) crea usuarios internos con turno, especialidad,
  zona y vehículo; crea clientes con o sin cuenta; muestra la guía funcional de cada rol.
- **Edición de pedidos**: `/pedidos/<id>/editar/` (admin/ventas) con formset de productos; se
  bloquea si `insumos_descontados` es True para no romper el inventario.
- **Admin enriquecido**: `UserAdmin` con `PerfilInline`, miniatura de producto, clientes con
  cuenta, y el estado del pedido es de solo lectura (solo cambia por `cambiar_estado`).
- **API solo admin**: `EsAdministrador`; ventas, cocina, calidad, despacho y cliente reciben 403.
- Flujo real: `recibido → confirmado → preparacion → horneado → calidad → listo → despachado →
  entregado`; retiro va de `listo → entregado` con `retirado_por`; cancelación repone insumos.
- `confirmado` exige pago registrado; `Pago` es el registro real y `estado_pago`/`saldo` se
  derivan. Agenda: 48 h web, 09:00–18:59 Santiago, cupo 6/día con rango local.
- **54 pruebas** en `api/tests.py`; `manage.py check` OK; `smoke_test.py` incluye `/health/` y
  `/equipo/`. Migración `0003` agrega atributos de perfil e imagen demo.
- PostgreSQL 16 en Docker (`localhost:5433`); si Docker no está activo, las pruebas pueden correr
  con `DB_ENGINE=sqlite`.

## Decisiones (y por qué)
- API solo administración: el panel HTML cubre la operación y evita duplicar reglas.
- Carrito en sesión: compra sin cuenta y precios siempre vigentes.
- Lógica en el modelo (`cambiar_estado`, `validar_agenda`, `descontar_insumos`, `reponer_insumos`).
- Permisos de transición en `Pedido.TRANSICIONES_ROL`; `api/roles.py` los traduce a la guía del rol.
- Imagen demo como `CharField` + propiedad `imagen_url`: el repo no versiona `media/` y el catálogo
  funciona tras clonar; la foto subida en Admin tiene prioridad.
- Editar un pedido con BOM descontado se bloquea: primero se cancela (repone) y se crea de nuevo.

## Aprendizajes y errores a evitar
- `ALLOWED_HOSTS` debe incluir la IP elástica de la EC2 o Django responde 400.
- `STATIC_ROOT` + `collectstatic` son obligatorios para Nginx (incluye las imágenes demo).
- Ocultar un botón no protege una regla: modelo y vista validan igual.
- Comparar fechas con `__date` desplaza el cupo por UTC; usar rango local.
- `UserAdmin` con `is_staff=True` para un rol no admin lo convertiría en admin: solo el rol
  Administrador recibe `is_staff`/`is_superuser`.
- El seed usa claves conocidas; en EC2 solo con `SEED_DEMO_DATA=true`.
- Un contexto nuevo en una vista puede romper toda una página sin que la suite lo note: cada
  página debe tener al menos una prueba de 200 por rol (pasó con `puede_editar`).

## Pendientes
- Completar la IP pública en `README.md`, desplegar en EC2 y configurar HTTPS.
- Reemplazar las fotos demo por fotografías propias antes de publicar.
- Opcional: impedir pagos que superen el saldo y notificar al cliente por correo.
