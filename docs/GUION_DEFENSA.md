# Guion de defensa — Dulce Arte (EVA 3 Backend)

Duración objetivo: **10 a 12 minutos** de demostración + preguntas.
Regla de oro: cada funcionalidad se muestra **primero en la interfaz** y luego se explica
**dónde está el código**.

## Antes de partir (2 minutos previos)

```powershell
.\env\Scripts\activate
docker compose up -d          # PostgreSQL
python manage.py migrate
python seed_data.py
python manage.py runserver
```

- Abrir `http://127.0.0.1:8000/` y dejar pestañas con `/tienda/`, `/equipo/`, `/admin/` y `/api/`.
- Usuario interno `admin` / `Dulce2026!`; cliente demo `cliente` / `Cliente2026!`.
- Tener a mano `api/models.py`, `api/views.py`, `api/carrito.py` y `api/forms.py`.

> En EC2: reemplazar `127.0.0.1:8000` por `http://IP_ELASTICA/`.

## 1. Presentación (1 min)

> "Dulce Arte es una pastelería artesanal que trabaja a pedido. Antes se coordinaba todo por
> cuaderno: se perdían fechas, se compraban insumos de más y no quedaba evidencia de la
> entrega. Ahora es una tienda en línea con agenda limitada: el cliente compra, paga un
> anticipo y sigue su pedido; el equipo trabaja en un panel interno con producción, insumos y
> despacho. La API REST quedó reservada a administración."

## 2. Tienda pública y carrito (2 min)

1. Abrir `/` → landing con productos y los pasos del pedido.
2. Ir a `/tienda/` → filtrar por categoría, mostrar las fotos del catálogo y la disponibilidad
   calculada.
3. Abrir un producto → ingredientes de la receta y campo de personalización.
4. Agregar al carrito con cantidad y una dedicatoria; abrir `/carrito/`.
5. Cambiar la cantidad y mostrar que el subtotal se recalcula.

> "El catálogo solo muestra productos activos. `Producto.unidades_disponibles` se calcula con
> el stock de los insumos de su receta; si no alcanza para una unidad, el producto aparece sin
> stock y no se puede agregar. El carrito vive en la sesión (`api/carrito.py`) y **nunca**
> guarda el precio: cada vez que se muestra se lee el precio vigente del catálogo."

> "Las fotos vienen de `static/IMAGES/productos/` para que el catálogo se vea real desde la
> primera ejecución. En el Admin se puede subir una foto propia por producto; `Producto.imagen_url`
> prioriza la subida y usa la demo solo como respaldo."

## 3. Checkout y agenda (2 min)

1. Ir a **Continuar al checkout**.
2. Mostrar que la fecha mínima es 48 horas adelante; elegir retiro o despacho.
3. Completar datos y confirmar → redirección al seguimiento con código `PED-000xx`.
4. (Opcional) Intentar una fecha dentro de 24 horas → el sistema la rechaza y explica el plazo.
5. Mencionar cupo diario de 6 y horario 09:00–18:59 de Santiago.

> "La agenda no es un adorno: `Pedido.validar_agenda` exige 48 horas para pedidos web, horario
> de atención y un cupo diario de 6 pedidos no cancelados. El cupo se cuenta con un rango de
> fecha local, no con `__date`, porque esa conversión aplica UTC y desplaza el día en Santiago.
> El checkout valida stock y agenda antes de crear el pedido, todo dentro de
> `transaction.atomic`; si algo falla, no queda nada a medias."

## 4. Seguimiento y cuenta de cliente (1,5 min)

1. En la página de seguimiento, copiar el código o el enlace con token.
2. Cerrar sesión / abrir ventana incógnita y buscar el pedido → se ve el avance sin datos
   personales.
3. Ingresar como `cliente` / `Cliente2026!` → `/mis-pedidos/` muestra solo sus pedidos.
4. Abrir el detalle de un pedido propio.

> "El seguimiento público funciona por código o por token. Nombre, teléfono y dirección solo se
> muestran al dueño del pedido o al personal interno (`_puede_ver_contacto`). El registro crea
> el `User`, el `Perfil` con rol cliente y la ficha `Cliente` vinculada; `mis-pedidos` filtra
> por esa ficha, así que un cliente nunca ve pedidos ajenos."

## 5. Panel interno y pagos (2 min)

1. Entrar con `admin` / `Dulce2026!` → panel con métricas y pedidos web nuevos.
2. Ir a **Pedidos** → abrir el pedido recién creado.
3. Mostrar que está **Recibido** y con pago pendiente.
4. Intentar pasarlo a **Confirmado** sin pago → error.
5. Registrar un pago (efectivo o transferencia) y luego confirmar.
6. Mostrar el cambio de estado y el historial con usuario y fecha.
7. Abrir **Editar pedido** → cambiar cantidad o dirección y guardar; luego mostrar que el botón
   desaparece cuando el pedido ya descontó insumos.

> "El pedido no entra a producción sin pago. `Pago` es un registro real con monto, método, tipo
> y responsable; `total_pagado`, `estado_pago` y `saldo` se calculan desde esos registros. El
> anticipo antiguo quedó solo como respaldo histórico. La transición a `confirmado` valida
> `estado_pago != pendiente` en `Pedido.cambiar_estado`."

## 6. Venta directa de mostrador (2 min)

1. Entrar con `ventas` / `Dulce2026!` → **Mostrador** (`/mostrador/`).
2. Buscar “chocolate” y mostrar el stock disponible calculado desde el BOM.
3. Agregar productos con cantidad; la venta se guarda en sesión y muestra el total.
4. Elegir un cliente registrado o escribir nombre y teléfono para crear la ficha.
5. Elegir **retiro** (se lo lleva el cliente) o **delivery**, registrar el pago y cerrar.
6. Mostrar el pedido resultante: estado **Entregado** o **Despachado**, badge “Venta directa”,
   insumos descontados y sin ocupar cupo de la agenda.
7. En `/pedidos/`, abrir un pedido **Listo** y mostrar las acciones “Vendido · entregado al
   cliente” y “Despachado · delivery”.

> "La venta de mostrador reutiliza `Pedido` con `venta_directa=True`: no inventa otra entidad ni
> otro flujo de pago. Al cerrar, `Pedido.cambiar_estado(..., venta_directa=True)` permite la ruta
> express `recibido → entregado` (retiro) o `recibido → despachado` (delivery), descuenta el BOM
> una sola vez y deja el historial. Solo admin y ventas pueden ejecutarla."

## 7. Kanban y BOM (2 min)

1. Anotar el stock de **Harina sin polvos** en `/inventario/`.
2. Ir a `/kanban/` y mover el pedido a **En preparación**.
3. Refrescar inventario → el stock bajó por la receta × cantidad.
4. Mostrar el detalle del pedido: “insumos descontados” e historial.
5. (Opcional) Cancelar un pedido preparado → el stock se repone con un movimiento de entrada.

> "El BOM es `RecetaInsumo` (producto ↔ insumo ↔ cantidad). El descuento ocurre una sola vez
> por la bandera `insumos_descontados`, con `transaction.atomic` y `select_for_update`. Si falta
> stock, se revierte todo y se listan los faltantes. Cancelar ejecuta `reponer_insumos`, que
> devuelve lo consumido y deja el movimiento de entrada como evidencia."

## 8. Despacho y retiro (1,5 min)

1. Ir a **Despachos** → asignar ruta a un pedido **Listo** con modalidad despacho.
2. Mostrar que el pedido pasó a **Despachado** y tiene fecha de salida.
3. Intentar confirmar sin evidencia o sin receptor → error.
4. Adjuntar una imagen como comprobante, escribir quién recibe y confirmar → **Entregado**.
5. En **Retiros pendientes**, escribir quién retira y cerrar un pedido de retiro.

> "Crear la ruta ya no entrega el pedido: lo deja en `despachado`. La entrega se cierra con
> receptor y firma o comprobante (`Despacho.clean`), y el retiro exige `retirado_por`. Ambas
> transiciones son atómicas y quedan en el historial."

## 9. Equipo, roles, Admin y API (2 min)

1. `/equipo/` → mostrar la guía de roles (responsabilidades, permisos, límites y transiciones) y
   crear un usuario de cocina con turno y especialidad, o un cliente con cuenta.
2. `/admin/` → cabecera, filtros, inlines del detalle y del BOM, pagos y miniatura de producto.
3. En el Admin de usuarios, abrir un usuario → el perfil y el rol se editan en la misma pantalla.
4. `/api/` → navegador DRF con sesión de `admin`.
5. Cerrar sesión, entrar como `ventas` y abrir `/api/pedidos/` → **403**.
6. Mostrar que `/pedidos/` y `/kanban/` funcionan por formularios, sin `fetch`.

> "Cada rol tiene atributos y permisos concretos. `Pedido.TRANSICIONES_ROL` es la única fuente de
> verdad: cocina no puede confirmar, ventas no puede iniciar producción, calidad aprueba y
> despacho entrega. El panel solo muestra las transiciones que el rol puede ejecutar y el modelo
> vuelve a validarlas, así que ocultar un botón no es la seguridad. La API es solo para
> administración: `EsAdministrador` cierra el resto con 403. Ningún template interno usa `/api/`
> ni `fetch`."

## 10. Modelo, verificación y cierre (1 min)

> "El modelo está en 3FN: categorías separadas, BOM en tabla intermedia, precio histórico en el
> detalle, pagos como registro, historial de estados y movimientos de inventario como auditoría.
> La app corre en EC2 con PostgreSQL, Gunicorn en socket Unix y Nginx como proxy inverso."

```powershell
python manage.py check
python manage.py test api      # 63 pruebas
python smoke_test.py           # no deja datos
```

> "El sistema cubre la venta completa y la operación interna: catálogo, agenda, pago, producción,
> insumos y entrega con evidencia, con la API cerrada a los roles que no la necesitan."

## Preguntas probables y respuesta corta

| Pregunta | Respuesta |
|---|---|
| ¿Por qué la API es solo para admin? | El panel HTML cubre la operación; tener permisos por rol en la API duplicaba reglas y ampliaba la superficie de ataque. `EsAdministrador` cierra el resto con 403. |
| ¿Dónde está la lógica de negocio? | En `models.py`: `cambiar_estado`, `validar_agenda`, `descontar_insumos`, `reponer_insumos`, `Despacho.clean`. Las vistas solo orquestan. |
| ¿Cómo se calcula el pago? | `total_pagado` suma los `Pago`; `estado_pago` es pendiente, parcial o pagado; `saldo = total − pagado`. Sin pagos no se confirma. |
| ¿Cómo evitas vender sin stock? | `Producto.unidades_disponibles` sale del BOM y el checkout compara cada línea antes de crear el pedido. |
| ¿Cómo funciona la agenda? | 48 h para web, 09:00–18:59 de Santiago y cupo de 6 por día; el pedido agendado de mostrador no exige anticipación pero sí horario y cupo; la venta directa no ocupa cupo. |
| ¿Cómo se registra una venta de mostrador? | `/mostrador/` arma una venta en sesión con precios y stock vigentes; al cerrar crea un `Pedido` con `venta_directa=True`, registra el pago y descuenta el BOM una sola vez. |
| ¿Cómo evitas descontar dos veces? | Bandera `insumos_descontados` + transacción atómica + `select_for_update`. |
| ¿Qué pasa si no hay stock? | `ValidationError` con los faltantes; la transacción se revierte y el pedido no cambia de estado. |
| ¿Se puede entregar sin evidencia? | No: el despacho exige receptor y firma o comprobante; el retiro exige `retirado_por`. |
| ¿Por qué el carrito no está en la base? | Se puede comprar sin cuenta; guardarlo en sesión evita tablas y limpieza de carritos abandonados. El precio se lee siempre del catálogo. |
| ¿Por qué PostgreSQL y no SQLite? | Requisito del ramo; además soporta concurrencia y `select_for_update`, que SQLite no. |
| ¿Qué pasa si dos usuarios mueven el pedido a la vez? | El flujo se valida contra el estado actual y el descuento bloquea las filas de insumos. |
| ¿Los roles son solo etiquetas? | No: `TRANSICIONES_ROL` limita cada avance y `cambiar_estado` valida el rol en el modelo; además cada rol tiene menú y páginas propias. |
| ¿Cómo se agregan fotos a los productos? | En el Admin (`Producto → Imagen del catálogo`) o con la ruta demo `imagen_estatica`; `imagen_url` resuelve la prioridad. |
| ¿Se puede editar un pedido ya producido? | No: al descontar insumos se bloquea la edición para no romper la trazabilidad; primero se cancela (repone) y se crea otro. |
| ¿Cómo se despliega? | EC2 Ubuntu, Postgres local, venv, `migrate`, `collectstatic`, Gunicorn en socket Unix y Nginx. |
| ¿Qué mejorarías? | Impedir pagos que superen el saldo, notificaciones automáticas, facturación electrónica y tests de carga. |
