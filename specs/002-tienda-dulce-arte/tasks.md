# Tasks 002 — Tienda en línea y API administrativa

Estado: todas completadas.

## Dominio y migraciones
- [x] Agregar `CategoriaProducto` y `Producto.categoria`.
- [x] Calcular `unidades_disponibles` y `disponible` desde el BOM.
- [x] Vincular `Cliente.user` (opcional) y exponer `tiene_cuenta`.
- [x] Agregar `canal`, `modalidad`, `direccion_entrega`, `telefono_contacto`, `retirado_por`.
- [x] Agregar `token_seguimiento`, `confirmado_en` y `confirmado_por`.
- [x] Incorporar el estado `confirmado` y las transiciones nuevas.
- [x] Implementar `Pedido.validar_agenda`, `clean` y `reponer_insumos`.
- [x] Crear `Pago` y `Despacho.confirmado_por`.
- [x] Generar y aplicar la migración `0002` con backfill de tokens.

## Tienda y cuenta
- [x] Carrito en sesión (`api/carrito.py`) con precios frescos.
- [x] Catálogo, detalle de producto, carrito, checkout y seguimiento.
- [x] Registro de cliente con `User` + `Perfil` + `Cliente`.
- [x] `mis-pedidos` y detalle restringido al dueño.
- [x] Seguimiento público por código o token sin datos personales.

## Panel interno
- [x] Formularios de pedido, pago, despacho, entrega y retiro.
- [x] Pedidos con filtros y alta de mostrador.
- [x] Kanban server-side con transiciones validadas.
- [x] Despachos: crear ruta, confirmar con evidencia y cerrar retiros.
- [x] Eliminar `static/js/pedidos.js` y `static/js/kanban.js`.

## API y seguridad
- [x] `EsAdministrador` como permiso global de DRF.
- [x] API cerrada para ventas, cocina, calidad, despacho y cliente.
- [x] Router con `pagos` y serializers actualizados.
- [x] Admin con categorías, pagos y estados de pago.

## Datos y verificación
- [x] Seed con categorías, 5 productos con BOM, cliente demo y pedidos con pagos.
- [x] 43 pruebas en `api/tests.py`.
- [x] `smoke_test.py` con tienda, panel, API cerrada y BOM con rollback.
- [x] `manage.py check` sin errores.

## Documentación
- [x] Spec, plan y tasks 002.
- [x] `README.md`, `MEMORY.md`, `GLOSSARY.md` y ADRs.
- [x] `docs/modelo_datos.md`, `docs/GUION_DEFENSA.md` y `prompts_ia.md`.
