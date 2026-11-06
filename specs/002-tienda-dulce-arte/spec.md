# Spec 002 — Tienda en línea y API administrativa (Dulce Arte)

Estado: implementada

## Contexto y objetivo
La spec 001 resolvió la trazabilidad interna, pero el negocio seguía sin poder vender:
no existía catálogo público, el pedido solo se registraba en mostrador, el estado
`despachado` no se usaba de verdad, el anticipo era un número suelto y cualquier rol podía
llamar la API. Esta spec convierte a Dulce Arte en una tienda real: el cliente compra en
línea, reserva su cupo, paga el anticipo, sigue su pedido y recibe con evidencia; el personal
trabaja en un panel server-side y la API REST queda reservada a administración.

## Usuarios / actores
- **Cliente**: navega el catálogo, compra con o sin cuenta, sigue su pedido y revisa su historial.
- **Ventas**: confirma pedidos, registra pagos y agenda pedidos de mostrador.
- **Cocina**: mueve el pedido por producción y consume insumos según la receta.
- **Control de calidad**: aprueba, devuelve o cierra la producción.
- **Despacho**: asigna rutas, confirma entregas y cierra retiros.
- **Administrador**: supervisa todo, usa el Admin de Django y es el único que puede usar la API.

## Historias de usuario
- HU-5. Como cliente quiero ver el catálogo con precios y disponibilidad para elegir qué comprar.
- HU-6. Como cliente quiero armar un carrito y reservar retiro o despacho sin crear cuenta.
- HU-7. Como cliente quiero pagar un anticipo y seguir mi pedido con un código.
- HU-8. Como cliente con cuenta quiero ver todos mis pedidos y sus estados de pago.
- HU-9. Como ventas quiero confirmar el pedido solo cuando el anticipo esté registrado.
- HU-10. Como despacho quiero que el pedido salga a reparto al crear la ruta y se cierre con evidencia.
- HU-11. Como administrador quiero una API para integraciones sin exponerla al resto de los roles.

## Requisitos funcionales (EARS)

### Catálogo y disponibilidad
- RF-19: EL SISTEMA muestra solo productos activos, con categoría, precio, porciones y disponibilidad.
- RF-20: EL SISTEMA calcula las unidades disponibles de un producto desde su receta y el stock de insumos; SI el producto no tiene receta, ENTONCES se considera disponible sin límite.
- RF-21: SI la receta no alcanza para una unidad, ENTONCES el producto se muestra como “Sin stock” y no permite agregarse al carrito.
- RF-22: CUANDO el cliente abre el detalle de un producto, EL SISTEMA muestra sus ingredientes y permite indicar una personalización.

### Carrito y checkout
- RF-23: EL SISTEMA mantiene el carrito en la sesión, sin exigir cuenta, guardando producto, cantidad y personalización.
- RF-24: EL SISTEMA recalcula los precios del carrito desde el catálogo vigente; nunca confía en un precio guardado en sesión.
- RF-25: EL SISTEMA limita cada línea del carrito a 50 unidades y elimina la línea cuando la cantidad llega a cero.
- RF-26: SI el carrito está vacío, ENTONCES el checkout redirige al catálogo con un aviso.
- RF-27: CUANDO el cliente confirma el checkout, EL SISTEMA valida stock, agenda y datos de entrega, y crea el pedido `canal=web`, estado `recibido`, con token de seguimiento y detalles con precio histórico, dentro de una transacción.
- RF-28: SI falta stock, ENTONCES EL SISTEMA no crea el pedido y lista los productos con problema.
- RF-29: EL SISTEMA cobra un costo fijo de despacho de $3.500; el retiro en tienda no tiene costo ni exige dirección.
- RF-30: EL SISTEMA exige aceptar las condiciones y elegir forma de pago; el pedido queda con pago pendiente hasta que ventas registre el abono.

### Agenda
- RF-31: SI el pedido es web, ENTONCES la entrega debe agendarse con al menos 48 horas de anticipación.
- RF-32: EL SISTEMA solo acepta entregas entre 09:00 y 18:59, hora de `America/Santiago`.
- RF-33: EL SISTEMA limita a 6 pedidos no cancelados por día y calcula el cupo con el rango de fecha local, no con UTC.
- RF-34: SI la modalidad es despacho, ENTONCES el pedido exige dirección de entrega.
- RF-35: EL SISTEMA permite agendar pedidos de mostrador sin el plazo de 48 horas, pero siempre respetando horario y cupo.

### Seguimiento y cuenta
- RF-36: EL SISTEMA permite seguir un pedido por código o token sin sesión, sin exponer nombre, teléfono ni dirección a terceros.
- RF-37: CUANDO una persona se registra, EL SISTEMA crea su usuario, su perfil `cliente` y su ficha de `Cliente` vinculada.
- RF-38: EL SISTEMA muestra a cada cliente solo sus propios pedidos.
- RF-39: SI un cliente intenta abrir el detalle de un pedido ajeno, ENTONCES EL SISTEMA lo redirige sin revelar datos.
- RF-40: EL SISTEMA permite al personal interno ver todos los pedidos y al cliente solo los suyos.

### Pagos
- RF-41: EL SISTEMA registra cada pago con monto, método (efectivo, transferencia o tarjeta), tipo, referencia y responsable.
- RF-42: EL SISTEMA calcula `total_pagado` como la suma de los pagos del pedido y usa el anticipo histórico solo como respaldo.
- RF-43: EL SISTEMA deriva `estado_pago` (pendiente, parcial o pagado) desde los pagos y calcula `saldo = total − total_pagado`.
- RF-44: SI el pedido no tiene ningún pago, ENTONCES no se puede confirmar.
- RF-45: EL SISTEMA rechaza pagos con monto menor o igual a cero.

### Flujo de producción y entrega
- RF-46: EL SISTEMA exige el paso `recibido → confirmado → preparacion → horneado → calidad → listo` antes de despachar o entregar.
- RF-47: CUANDO el pedido pasa a `preparacion`, EL SISTEMA descuenta los insumos del BOM una sola vez y de forma atómica.
- RF-48: CUANDO un pedido con insumos descontados se cancela, EL SISTEMA repone el stock con movimientos de entrada.
- RF-49: CUANDO se crea un despacho para un pedido `listo`, EL SISTEMA lo deja en `despachado` y guarda la salida.
- RF-50: SI se intenta confirmar una entrega sin receptor, firma o comprobante, ENTONCES EL SISTEMA rechaza la operación.
- RF-51: CUANDO se confirma el despacho, EL SISTEMA deja el pedido en `entregado` de forma atómica.
- RF-52: SI el pedido es de retiro, ENTONCES solo puede pasar a `entregado` registrando quién lo retira.
- RF-53: EL SISTEMA registra cada cambio de estado en `HistorialEstado` con usuario, fecha y comentario.

### Panel interno y API
- RF-54: EL SISTEMA opera pedidos, Kanban, inventario, pagos, despachos y retiros con formularios Django server-side.
- RF-55: LA API REST solo permite lectura y escritura al rol administrador; los demás roles reciben 403 y los anónimos 401/403.
- RF-56: EL SISTEMA no permite que las pantallas internas ni la tienda dependan de `fetch` a `/api/`.
- RF-57: LA API expone pedidos, clientes, productos, insumos, despachos, pagos y movimientos, además de las acciones `cambiar_estado` y `descontar_insumos`.
- RF-58: SI un pedido ya consumió insumos, ENTONCES la API no permite eliminarlo.

## Requisitos no funcionales
- RNF-5: Interfaz responsiva en español, con templates Django, CSS propio y JS nativo sin frameworks ni bundler.
- RNF-6: Fechas y cupos en `America/Santiago`; nunca comparar con UTC.
- RNF-7: PostgreSQL 16 en EC2 y Docker local; SQLite solo para pruebas rápidas.
- RNF-8: El seed es idempotente y crea un cliente demo con cuenta (`cliente` / `Cliente2026!`).
- RNF-9: `smoke_test.py` no deja datos: envuelve las pruebas de negocio en una transacción con rollback.
- RNF-10: La API sigue disponible para administración con sesión y CSRF, sin exponer credenciales en el repositorio.

## Casos límite
- Fecha con cupo completo o fuera de horario.
- Producto sin receta definida (disponible sin límite) y producto con stock insuficiente.
- Cliente que compra sin cuenta y luego se registra con el mismo correo.
- Token de seguimiento inválido o pedido inexistente.
- Pedido cancelado que ya había descontado insumos.
- Pago parcial, pago completo y pedido sin pagos.
- Despacho sin dirección, sin receptor o sin evidencia.
- Cliente que intenta abrir la API o un pedido ajeno.

## Fuera de alcance
- Pasarela de pago en línea y facturación electrónica.
- Notificaciones automáticas por correo o WhatsApp.
- Cupones, puntos de fidelidad y multi-sucursal.
- Aplicación móvil nativa.

## Criterios de finalización
- `python manage.py check` sin errores y `python manage.py test api` con las 43 pruebas OK.
- `python smoke_test.py` valida tienda, panel interno, API cerrada a roles operativos y BOM con rollback.
- Un pedido web no se crea sin stock, sin cupo, fuera de horario o sin las 48 horas.
- No se confirma sin pago, no se entrega sin evidencia o sin quién retira, y la cancelación repone insumos.
- Ningún template interno usa `/api/` ni `fetch(`.

## Dudas abiertas
- Ninguna.
