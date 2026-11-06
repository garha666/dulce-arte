# Plan 002 — Tienda en línea y API administrativa

## Archivos y responsabilidades
| Archivo | Responsabilidad | RF |
|---|---|---|
| `api/models.py` | Categorías de producto, agenda (`validar_agenda`), estados `confirmado`/`despachado`, `Pago`, `reponer_insumos`, `Cliente.user` | RF-19…RF-53 |
| `api/carrito.py` | Carrito en sesión con precios frescos y totales | RF-23…RF-25 |
| `api/forms.py` | Registro, checkout, pedido interno, pago, despacho, entrega y seguimiento | RF-27…RF-58 |
| `api/views.py` | Tienda, checkout, seguimiento, cuenta, panel interno y API admin-only | RF-19…RF-58 |
| `api/urls.py` | Rutas públicas, internas y router DRF (incluye `pagos`) | RF-36…RF-57 |
| `api/permissions.py` | `EsAdministrador`: única llave de la API | RF-55 |
| `api/roles.py` | Rol `cliente`, menú de tienda y `ROLES_INTERNOS` | RF-37…RF-40 |
| `api/context_processors.py` | Expone rol, menú y unidades del carrito a todos los templates | RF-23, RF-54 |
| `api/admin.py` | Admin de categorías, pagos, cuentas vinculadas y estados de pago | RF-19, RF-41…RF-43 |
| `templates/tienda.html`, `producto_detalle.html`, `carrito.html`, `checkout.html`, `seguimiento.html`, `registro.html`, `mis_pedidos.html` | Tienda pública y cuenta | RF-19…RF-45 |
| `templates/pedidos.html`, `kanban.html`, `despachos.html`, `pedido_detalle.html` | Panel interno sin fetch | RF-46…RF-54 |
| `seed_data.py` | Catálogo con BOM, cliente con cuenta y pedidos que recorren el flujo real | RNF-8 |
| `smoke_test.py` | Verificación no destructiva de tienda, panel y API | RNF-9 |

## Decisiones técnicas (y alternativa descartada)
- **API solo administración**: se descartó mantener permisos por rol en la API porque el panel
  interno ya cubre a ventas, cocina, calidad y despacho; dos caminos duplicaban reglas y
  superficie de ataque.
- **Panel server-side**: se descartó el Kanban con `fetch` porque el estado debe validarse igual
  que en el modelo y el JS duplicaba transiciones y escapes.
- **Carrito en sesión**: se descartó un modelo `Carrito` en base de datos porque el cliente puede
  comprar sin cuenta; el precio siempre se lee del catálogo.
- **Pagos como registro**: se descartó seguir usando solo `anticipo` como número porque no permitía
  abonos parciales, métodos ni auditoría; `estado_pago` y `saldo` se derivan.
- **`confirmado` como paso real**: se descartó pasar de `recibido` a `preparacion` porque producción
  necesita una señal comercial (pago registrado) antes de consumir insumos.
- **`despachado` real**: se descartó usar `entregado` al crear la ruta; ahora la ruta marca salida y
  la evidencia cierra la entrega.
- **Agenda con rango local**: se descartó `fecha_entrega__date` porque convertía a UTC y movía el
  cupo diario de Santiago.

## Algoritmos

### Checkout
```
si el carrito está vacío: volver al catálogo
validar stock de cada línea contra unidades_disponibles
crear o reutilizar Cliente (vinculado al usuario si hay sesión)
crear Pedido(canal=web, estado=recibido, token)
validar agenda (48 h, horario, cupo, dirección si despacho)
crear PedidoDetalle con precio histórico
vaciar carrito y redirigir al seguimiento
(todo dentro de transaction.atomic)
```

### Pago
```
total_pagado = suma(pagos.monto) o anticipo histórico si no hay pagos
estado_pago = pendiente si 0 · parcial si < total · pagado si >= total
saldo = total - total_pagado
confirmar solo si estado_pago != pendiente
```

### Despacho y retiro
```
crear despacho de pedido listo:
    validar dirección y pedido listo
    guardar fecha_salida
    pedido.cambiar_estado("despachado")
confirmar entrega:
    exigir receptor + (firma o comprobante)
    guardar fecha_entrega y confirmado_por
    pedido.cambiar_estado("entregado")
retiro:
    exigir retirado_por
    pedido.cambiar_estado("entregado")
```

## Interfaz
- Tienda con filtros por categoría, disponibilidad calculada y carrito visible en la barra.
- Checkout en dos columnas: datos/entrega y resumen con costo de despacho.
- Seguimiento público con línea de tiempo; datos personales solo para el dueño o personal interno.
- Panel interno: listado con filtros, Kanban con botones de transición, despachos con evidencia y
  retiros con nombre de quien retira.

## Estrategia de verificación
`manage.py test api` cubre flujo, pagos, agenda, despacho, tienda, cuenta, API admin-only, BOM y
protección del frontend. `smoke_test.py` recorre páginas públicas e internas, comprueba 403 para
ventas/cocina/cliente en la API y valida descuento/reposición de stock con rollback.
