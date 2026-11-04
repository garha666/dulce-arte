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

- Abrir `http://127.0.0.1:8000/` y dejar una pestaña con `/admin/` y otra con `/api/`.
- Usuario `admin` / `Dulce2026!`.
- Tener a mano `api/models.py`, `api/admin.py` y `api/views.py`.

> En EC2: reemplazar `127.0.0.1:8000` por `http://IP_ELASTICA/`.

## 1. Presentación (1 min)

> "Dulce Arte es una pastelería artesanal. El problema es que los pedidos personalizados se
> coordinaban por cuaderno: se perdían fechas, se compraban insumos de más y no quedaba
> evidencia de la entrega. La solución es un sistema Django + DRF + PostgreSQL con cuatro
> funcionalidades: cotización, tablero Kanban, descuento de insumos por receta y despacho
> con confirmación."

## 2. Sitio público y login (1 min)

1. Abrir `/quienes-somos/`, `/servicios/` y `/contacto/`.
2. Enviar el formulario de contacto → mensaje de éxito.
3. Mostrar los botones **API** y **Admin** en la barra superior.
4. Entrar con `admin` / `Dulce2026!`.

> "Las páginas públicas no requieren sesión; el panel de gestión y la API sí
> (`IsAuthenticated` en `settings.py`)."

## 3. Cotización de un pedido (2 min)

1. Ir a **Pedidos**.
2. Elegir cliente, fecha de entrega, producto y cantidad; escribir un diseño.
3. Registrar → aparece en la tabla con código `PED-000xx`, estado *Recibido* y total calculado.
4. Abrir el detalle del pedido → mostrar total, anticipo y saldo.

> "El pedido se crea por `POST /api/pedidos/`. El total se calcula en el modelo
> (`Pedido.total` = suma de subtotales + despacho; `saldo` = total − anticipo). El precio
> unitario se copia al detalle para conservar el precio histórico aunque el producto suba."

## 4. Tablero Kanban y trazabilidad (2 min)

1. Ir a **Cocina (Kanban)**.
2. Mover el pedido nuevo a *En preparación* → la tarjeta cambia de columna.
3. Abrir el detalle → el historial muestra el cambio con usuario y fecha.

> "Las transiciones están en `Pedido.TRANSICIONES` y solo se pueden ejecutar por
> `Pedido.cambiar_estado`. Si se pide una transición inválida, la API responde 400 y el
> pedido no cambia. Cada cambio queda en `HistorialEstado`."

4. (Opcional, evidencia técnica) En la consola:

```powershell
python smoke_test.py
```

> Mostrar la línea `Transición inválida -> HTTP 400`.

## 5. Descuento de insumos por BOM (2 min)

1. Anotar el stock de **Harina sin polvos** en **Insumos**.
2. Volver al Kanban y mover un pedido *Recibido* a *En preparación*.
3. Refrescar **Insumos** → el stock bajó exactamente por la receta × cantidad.
4. En el detalle del pedido, sección **Insumos** → "ya fueron descontados".

> "El BOM es la tabla intermedia `RecetaInsumo` (producto ↔ insumo ↔ cantidad), igual al
> ejemplo libro–autor de la unidad de normalización. El descuento ocurre una sola vez por
> la bandera `insumos_descontados`, dentro de `transaction.atomic` y con `select_for_update`
> para evitar que dos pedidos simultáneos sobregiren el stock. Si falta stock, se cancela
> todo y se listan los faltantes."

## 6. Despacho con evidencia (2 min)

1. Ir a **Despachos**.
2. Crear el despacho de un pedido *Listo* con dirección.
3. Intentar confirmar sin archivo → error (lo valida `Despacho.clean`).
4. Adjuntar una imagen como firma o comprobante, escribir el receptor y confirmar.
5. Mostrar el estado *Confirmado* y el enlace a la evidencia.

> "La entrega no se puede cerrar sin firma ni comprobante; es una regla de negocio del
> modelo, no solo del formulario."

## 7. Admin y API (1 min)

1. `/admin/` → mostrar cabecera personalizada, filtros, búsqueda e inlines
   (detalle del pedido e ingredientes del BOM).
2. `/api/` → mostrar el navegador DRF y `/api/pedidos/`.
3. Cerrar sesión y abrir `/api/pedidos/` → redirección/401.

> "La API usa ViewSets y DefaultRouter, como pide la receta del ramo. Los catálogos son de
> solo lectura para usuarios que no son administradores; el Kanban solo lo mueven cocina,
> calidad y admin (`api/permissions.py`)."

## 8. Modelo y despliegue (1 min)

> "El modelo está en 3FN: categorías e insumos separados, BOM en tabla intermedia, precio
> histórico en el detalle, historial de estados y movimientos de inventario como auditoría.
> La app corre en una instancia EC2 con PostgreSQL, Gunicorn como servicio systemd y Nginx
> como proxy inverso sirviendo estáticos."

## Preguntas probables y respuesta corta

| Pregunta | Respuesta |
|---|---|
| ¿Por qué 3FN? | Evita redundancia y anomalías de actualización: la categoría no se repite en cada insumo y la receta vive en `RecetaInsumo`. |
| ¿Dónde está la lógica de negocio? | En `models.py`: `cambiar_estado`, `descontar_insumos`, `Despacho.clean`. Las vistas solo orquestan. |
| ¿Cómo evitas descontar dos veces? | Bandera `insumos_descontados` + transacción atómica. |
| ¿Qué pasa si no hay stock? | `ValidationError` con los faltantes; la transacción se revierte y el pedido no cambia de estado. |
| ¿Cómo se protege la API? | `IsAuthenticated` global, permisos por rol y CSRF en el JS con `X-CSRFToken`. |
| ¿Por qué PostgreSQL y no SQLite? | Requisito del ramo; además soporta concurrencia y `select_for_update`, que SQLite no. |
| ¿Qué pasa si dos usuarios mueven el pedido a la vez? | El flujo se valida contra el estado actual y el descuento bloquea las filas de insumos. |
| ¿Cómo se despliega? | EC2 Ubuntu, Postgres local, venv, `migrate`, `collectstatic`, Gunicorn en socket Unix y Nginx. |
| ¿Qué hace el Admin? | Gestión de todos los modelos con filtros, búsqueda, inlines y una acción masiva para pasar pedidos a *Listo*. |
| ¿Qué mejorarías? | Notificaciones al cliente, facturación electrónica y tests de carga; hoy están fuera de alcance. |

## Cierre (30 s)

> "El sistema permite trazabilidad completa: desde la cotización, pasando por producción y
> consumo de insumos, hasta la entrega con evidencia. Todo queda auditado y las reglas se
> validan en el modelo, por lo que la interfaz web y la API se comportan igual."
