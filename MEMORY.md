# MEMORY.md — Dulce Arte

Memoria del proyecto entre sesiones. Máximo ~50 líneas.

## Estado actual
- Proyecto Django `drf` + app `api`; dominio en 3FN con insumos, BOM, pedidos, historial,
  movimientos, pagos, despachos, perfiles y cuentas de cliente.
- **Tienda completa**: catálogo por categorías, disponibilidad desde el BOM, carrito en sesión,
  checkout con retiro/despacho, seguimiento por código o token, registro y `mis-pedidos`.
- **Panel interno server-side**: pedidos, Kanban, inventario, pagos, despachos y retiros con
  formularios Django. Se eliminaron `pedidos.js` y `kanban.js`; ninguna pantalla usa `/api/`.
- **API solo admin**: `EsAdministrador` es el permiso global de DRF; ventas, cocina, calidad,
  despacho y cliente reciben 403 (anónimo 401/403). La API incluye `pagos`.
- Flujo real: `recibido → confirmado → preparacion → horneado → calidad → listo → despachado →
  entregado`; retiro va de `listo → entregado` con `retirado_por`; cancelación repone insumos.
- `confirmado` exige pago registrado; `Pago` es el registro real y `estado_pago`/`saldo` se
  derivan (con `anticipo` solo como respaldo histórico).
- Agenda: 48 h para web, 09:00–18:59 en `America/Santiago`, cupo de 6 por día contado con rango
  de fecha local (no `__date`, que aplica UTC).
- **43 pruebas automáticas** en `api/tests.py`: todas OK (flujo, pagos, agenda, despacho, tienda,
  cuenta, API admin-only, BOM y protección del frontend).
- Verificado: `manage.py check` OK; `smoke_test.py` recorre tienda y panel, comprueba 403 en la
  API y valida descuento/reposición de stock con transacción y rollback.
- PostgreSQL 16 en Docker (`localhost:5433`); migración `0002` aplicada con backfill de tokens.

## Decisiones (y por qué)
- API solo administración: el panel HTML ya cubre la operación y evita duplicar reglas y permisos.
- Carrito en sesión: permite comprar sin cuenta y el precio siempre se lee del catálogo vigente.
- Lógica en el modelo (`cambiar_estado`, `validar_agenda`, `descontar_insumos`, `reponer_insumos`,
  `Pago`): las vistas solo orquestan.
- `confirmado` y `despachado` son estados reales; la entrega se cierra con evidencia o con quién
  retira.
- Pago manual (efectivo/transferencia/tarjeta) sin pasarela ni facturación electrónica.
- SQLite solo para pruebas rápidas; la entrega usa PostgreSQL en EC2 (Docker local en 5433).

## Aprendizajes y errores a evitar
- `ALLOWED_HOSTS` debe incluir la IP elástica de la EC2, o Django responde 400.
- `STATIC_ROOT` + `collectstatic` son obligatorios para que Nginx sirva Admin y DRF.
- Ocultar un botón no protege una regla: el modelo y la vista deben validar igual.
- Comparar fechas de agenda con `__date` desplaza el cupo diario por UTC; usar rango local.
- El seed crea claves conocidas: `instalar.sh` no lo ejecuta por defecto
  (`SEED_DEMO_DATA=true` es explícito) y genera claves aleatorias.

## Pendientes
- Completar la IP pública en `README.md` y verificar el despliegue en EC2.
- Configurar HTTPS en Nginx y activar `DJANGO_SECURE_COOKIES=True` en la instancia.
- Opcional: impedir pagos que superen el saldo del pedido y notificar al cliente por correo.
