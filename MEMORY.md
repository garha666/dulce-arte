# MEMORY.md — Dulce Arte

Memoria del proyecto entre sesiones. Máximo ~50 líneas.

## Estado actual
- Django `drf` + app `api`; dominio en 3FN con insumos, BOM, pedidos, historial, movimientos,
  pagos, despachos, perfiles y cuentas de cliente.
- **Tienda completa con imágenes**: catálogo, carrito en sesión, checkout, seguimiento, registro y
  `mis-pedidos`; cada producto usa la foto del Admin o una imagen demo de `static/IMAGES/productos/`.
- **Panel interno server-side**: pedidos, Kanban, inventario, pagos, despachos y retiros; las
  acciones se filtran por rol (`Pedido.TRANSICIONES_ROL`).
- **Equipo y roles**: `/equipo/` (solo admin) crea usuarios internos con turno, especialidad, zona
  y vehículo, y clientes con o sin cuenta; muestra la guía funcional de cada rol.
- **Mostrador**: `/mostrador/` (admin/ventas) busca productos de vitrina con stock, arma la venta en
  sesión (`api/mostrador.py`), elige o crea cliente, cobra y cierra como retiro (`entregado`) o
  delivery (`despachado`). La venta directa descuenta insumos al cerrar y no ocupa cupo de agenda.
- **Edición de pedidos**: `/pedidos/<id>/editar/` (admin/ventas) con formset de productos; se
  bloquea si `insumos_descontados` es True para no romper el inventario.
- **Admin enriquecido**: `UserAdmin` con `PerfilInline`, miniatura de producto, clientes con
  cuenta, y el estado del pedido es de solo lectura (solo cambia por `cambiar_estado`).
- **API solo admin**: `EsAdministrador`; ventas, cocina, calidad, despacho y cliente reciben 403.
- Flujo real: `recibido → confirmado → preparacion → horneado → calidad → listo → despachado →
  entregado`; retiro va de `listo → entregado` con `retirado_por`; cancelación repone insumos.
- `confirmado` exige pago registrado; `Pago` es el registro real y `estado_pago`/`saldo` se
  derivan. Agenda: 48 h web, 09:00–18:59 Santiago, cupo 6/día con rango local.
- **63 pruebas** en `api/tests.py`; `manage.py check` OK; `smoke_test.py` cubre `/health/`,
  `/equipo/` y `/mostrador/`. Migración `0004` agrega `Pedido.venta_directa`.
- PostgreSQL 16 en Docker (`localhost:5433`); sin Docker, usar `DB_ENGINE=sqlite` para pruebas.
- **Desplegado en AWS EC2** (11-11-2026): `i-04ad1331475c6def0` (t3.micro, Ubuntu 22.04,
  us-east-1), Elastic IP `23.23.34.184`, PostgreSQL local, Gunicorn + Nginx y seed demo cargado.

## Decisiones (y por qué)
- API solo administración: el panel HTML cubre la operación y evita duplicar reglas.
- Carrito en sesión: compra sin cuenta y precios siempre vigentes.
- Lógica en el modelo (`cambiar_estado`, `validar_agenda`, `descontar_insumos`, `reponer_insumos`).
- Permisos de transición en `Pedido.TRANSICIONES_ROL`; `api/roles.py` los traduce a la guía del rol.
- Imagen demo como `CharField` + propiedad `imagen_url`: el repo no versiona `media/` y el catálogo
  funciona tras clonar; la foto subida en Admin tiene prioridad.
- Editar un pedido con BOM descontado se bloquea: primero se cancela (repone) y se crea de nuevo.
- Venta directa como `Pedido` con `venta_directa=True`: reutiliza pagos, BOM e historial sin otro
  modelo; el estado se cierra con una ruta express solo para admin/ventas.

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
- Configurar HTTPS (Nginx + certificado) y restringir el puerto 22 a una IP fija; cambiar las
  claves demo antes de exponer la instancia.
- Reemplazar las fotos demo por fotografías propias antes de publicar.
- Opcional: impedir pagos que superen el saldo y notificar al cliente por correo.
