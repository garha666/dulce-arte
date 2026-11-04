# Modelo de datos — Dulce Arte (3FN)

Justificación del diseño relacional usada en la defensa.

## 1FN — campos atómicos
Ningún campo guarda listas ni valores compuestos: el nombre y el teléfono del cliente son
campos separados; los ingredientes de una receta no viven dentro de `Producto`.

## 2FN — dependencia total de la clave
Cada tabla tiene su propia PK y todos sus atributos dependen de ella. El detalle del pedido
(`PedidoDetalle`) depende de su PK y referencia al pedido y al producto; no repite el nombre
del producto ni el nombre del cliente.

## 3FN — sin dependencias transitivas
Los datos de una entidad no se repiten en otra tabla:

| Dato | Dónde vive | Por qué |
|---|---|---|
| Categoría del insumo | `CategoriaInsumo` | si estuviera en `Insumo` se repetiría en cada fila |
| Precio del producto | `Producto` | el detalle guarda el precio **histórico** al momento de la venta |
| Insumos de la receta | `RecetaInsumo` (BOM) | tabla intermedia: producto ↔ insumo ↔ cantidad |
| Estados del pedido | `HistorialEstado` | trazabilidad: se guarda cada cambio, no solo el último |
| Consumos de stock | `MovimientoInsumo` | auditoría del descuento por BOM |
| Rol del usuario | `Perfil` (1:1 con `User`) | no se altera la tabla de autenticación de Django |

`RecetaInsumo` es el equivalente a la tabla intermedia libro–autor del material de
normalización: evita repetir la receta completa en cada producto y permite reutilizar insumos.

## Relaciones principales
```
User 1───1 Perfil
CategoriaInsumo 1───* Insumo
Producto 1───* RecetaInsumo *───1 Insumo        (BOM)
Cliente 1───* Pedido 1───* PedidoDetalle *───1 Producto
Pedido 1───* HistorialEstado
Pedido 1───* MovimientoInsumo
Pedido 1───1 Despacho
```

## Reglas de integridad
- `on_delete=PROTECT` en catálogos referenciados (insumo, producto, cliente): no se borra
  un insumo que tenga recetas o consumos.
- `on_delete=CASCADE` en detalle e historial: dependen totalmente del pedido.
- Restricción `UniqueConstraint(producto, insumo)` evita duplicar un ingrediente en la receta.
- Stock con `DecimalField(10,3)` para admitir gramos y mililitros sin errores de redondeo.
