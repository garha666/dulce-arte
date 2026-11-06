# Modelo de datos — Dulce Arte (3FN)

Justificación del diseño relacional usada en la defensa.

## 1FN — campos atómicos
Ningún campo guarda listas ni valores compuestos: el nombre y el teléfono del cliente son
campos separados; los ingredientes de una receta no viven dentro de `Producto`; la dirección de
despacho es un campo propio del pedido y no una cadena con modalidad y fecha mezcladas.

## 2FN — dependencia total de la clave
Cada tabla tiene su propia PK y todos sus atributos dependen de ella. El detalle del pedido
(`PedidoDetalle`) depende de su PK y referencia al pedido y al producto; no repite el nombre
del producto ni el nombre del cliente. `Pago` depende de su PK y referencia al pedido; no repite
el total ni el nombre del cliente.

## 3FN — sin dependencias transitivas
Los datos de una entidad no se repiten en otra tabla:

| Dato | Dónde vive | Por qué |
|---|---|---|
| Categoría del insumo | `CategoriaInsumo` | si estuviera en `Insumo` se repetiría en cada fila |
| Categoría del producto | `CategoriaProducto` | agrupa el catálogo sin repetir el nombre en cada producto |
| Precio del producto | `Producto` | el detalle guarda el precio **histórico** al momento de la venta |
| Insumos de la receta | `RecetaInsumo` (BOM) | tabla intermedia: producto ↔ insumo ↔ cantidad |
| Estados del pedido | `HistorialEstado` | trazabilidad: se guarda cada cambio, no solo el último |
| Consumos de stock | `MovimientoInsumo` | auditoría del descuento y de la reposición por cancelación |
| Rol del usuario | `Perfil` (1:1 con `User`) | no se altera la tabla de autenticación de Django |
| Cuenta del cliente | `Cliente.user` (1:1 opcional) | una ficha puede existir sin cuenta (venta de mostrador) |
| Pagos del pedido | `Pago` | cada abono tiene monto, método, fecha y responsable propios |
| Estado de pago y saldo | Se **calculan** desde `Pago` | guardarlos duplicaría un dato derivado y podría desincronizarse |
| Disponibilidad del producto | Se **calcula** desde el BOM | el stock cambia a diario; guardarlo quedaría obsoleto |

`RecetaInsumo` es el equivalente a la tabla intermedia libro–autor del material de
normalización: evita repetir la receta completa en cada producto y permite reutilizar insumos.

## Relaciones principales
```
User 1───1 Perfil
User 1───0..1 Cliente
CategoriaInsumo 1───* Insumo
CategoriaProducto 1───* Producto
Producto 1───* RecetaInsumo *───1 Insumo        (BOM)
Cliente 1───* Pedido 1───* PedidoDetalle *───1 Producto
Pedido 1───* HistorialEstado
Pedido 1───* MovimientoInsumo                   (consumo / entrada)
Pedido 1───* Pago
Pedido 1───1 Despacho
```

## Reglas de integridad
- `on_delete=PROTECT` en catálogos referenciados (insumo, producto, cliente): no se borra un
  insumo que tenga recetas o consumos, ni un cliente con pedidos.
- `on_delete=CASCADE` en detalle, historial, pagos y movimientos: dependen totalmente del pedido.
- `on_delete=SET_NULL` en `Cliente.user`: borrar una cuenta no borra la ficha ni su historial.
- Restricción `UniqueConstraint(producto, insumo)` evita duplicar un ingrediente en la receta.
- Stock con `DecimalField(10,3)` para admitir gramos y mililitros sin errores de redondeo.
- `Pago.monto > 0`; el estado de pago y el saldo se derivan de la suma de pagos.
- `token_seguimiento` es único y se genera al crear el pedido; la migración `0002` hizo backfill
  de los pedidos existentes.
- Agenda: `fecha_entrega` se valida contra 48 horas (web), horario 09:00–18:59 de
  `America/Santiago` y cupo de 6 pedidos no cancelados por día, contado con rango de fecha local.
- Un pedido con `insumos_descontados=True` no se elimina; si se cancela, `reponer_insumos`
  devuelve el stock con movimientos de tipo entrada.
