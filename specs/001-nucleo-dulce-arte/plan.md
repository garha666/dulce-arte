# Plan 001 — Núcleo de trazabilidad

## Archivos y responsabilidades
| Archivo | Responsabilidad | RF |
|---|---|---|
| `api/models.py` | Entidades en 3FN, cálculo de totales, `TRANSICIONES`, `cambiar_estado`, `descontar_insumos`, `Despacho.clean` | RF-1…RF-16 |
| `api/admin.py` | Registro y personalización de todos los modelos, inlines de BOM y detalle | RF-2, RF-7, RF-15 |
| `api/serializers.py` | Validación de la API, anidamiento de detalles e historial | RF-1…RF-4, RF-13, RF-14 |
| `api/views.py` | ViewSets, acciones `cambiar_estado` / `descontar_insumos` y vistas HTML | RF-5…RF-16 |
| `api/permissions.py` | Restricción del Kanban a cocina/calidad/admin | RNF-2 |
| `templates/kanban.html` + `static/js/kanban.js` | Tablero y consumo asíncrono con `X-CSRFToken` | RF-5, RF-7 |
| `seed_data.py` | Datos de demostración para la defensa | — |

## Decisiones técnicas (y alternativa descartada)
- **Lógica en el modelo**, no en el serializer: se descartó duplicar la validación en la API y en
  las vistas HTML porque producía comportamientos distintos.
- **`select_for_update`** al descontar stock: se descartó leer-modificar-escribir simple porque
  dos pedidos simultáneos podían sobregirar el inventario.
- **Bandera `insumos_descontados`**: se descartó calcular el descuento "por diferencia" del historial,
  porque es más costoso y difícil de auditar.
- **Vistas HTML con templates** (no SPA): lo exige la receta del ramo y simplifica el despliegue.

## Algoritmo de descuento (pseudocódigo)
```
si pedido.insumos_descontados: terminar
requeridos = {}
para cada detalle del pedido:
    para cada ingrediente de la receta del producto:
        requeridos[insumo] += ingrediente.cantidad * detalle.cantidad
bloquear filas de insumos involucrados
si algún insumo.stock < requerido: error con la lista de faltantes
para cada insumo:
    stock -= requerido
    guardar movimiento de tipo consumo
marcar pedido.insumos_descontados = True
```

## Interfaz
- Kanban con una columna por estado y botones con las transiciones válidas.
- Pedidos: formulario que crea vía `POST /api/pedidos/` y tabla que se recarga con `GET`.
- Despachos: formulario multipart con firma o comprobante.

## Estrategia de verificación
`smoke_test.py` con el cliente de Django: login, 200 en todas las páginas, transición válida
(200 + stock descontado) y transición inválida (400).
