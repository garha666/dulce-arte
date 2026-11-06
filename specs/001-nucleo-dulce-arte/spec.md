# Spec 001 — Núcleo de trazabilidad de pedidos (Dulce Arte)

Estado: implementada. La spec 002 reemplaza el acceso de la API (ahora solo administración), el
flujo de estados (agrega `confirmado` y usa `despachado`) y el modelo de pagos (ver spec 002).

## Contexto y objetivo
La pastelería Dulce Arte coordina pedidos personalizados entre ventas, cocina y despacho.
Hoy esa coordinación es manual, lo que produce entregas tardías, insumos vencidos y
entregas sin comprobante. El objetivo es registrar el pedido completo, seguir su avance en
cocina, descontar los insumos según la receta y confirmar la entrega con evidencia.

## Usuarios / actores
- **Ventas**: cotiza y registra pedidos.
- **Cocina**: mueve el pedido por el tablero de producción.
- **Control de calidad**: aprueba o devuelve el pedido antes del despacho.
- **Despacho**: asigna la ruta y confirma la entrega.
- **Administrador**: gestiona catálogos, usuarios y supervisa todo.

## Historias de usuario
- HU-1. Como vendedor quiero cotizar un pedido con ingredientes, diseño y fecha para comprometer un precio y una hora de entrega.
- HU-2. Como cocina quiero ver los pedidos en columnas para saber qué preparar primero.
- HU-3. Como bodega quiero que el sistema descuente los insumos para no producir sin stock.
- HU-4. Como despacho quiero registrar la entrega con firma o foto para tener evidencia.

## Requisitos funcionales (EARS)

### Cotización y registro de pedidos
- RF-1: CUANDO el usuario registra un pedido con cliente, fecha de entrega y al menos un producto, EL SISTEMA crea el pedido en estado "Recibido" con un código único `PED-00001`.
- RF-2: CUANDO se agrega un producto al pedido sin precio unitario, EL SISTEMA toma el precio base vigente del producto.
- RF-3: EL SISTEMA calcula el total como la suma de los subtotales de los detalles más el costo de despacho, y muestra el saldo como total menos anticipo.
- RF-4: SI el pedido no tiene detalles, ENTONCES EL SISTEMA no permite confirmar la cotización.

### Tablero Kanban de cocina
- RF-5: CUANDO el usuario mueve un pedido, EL SISTEMA solo acepta las transiciones definidas (Recibido → En preparación → Horneado/Decorado → Control de calidad → Listo → Despachado → Entregado).
- RF-6: SI la transición solicitada no está permitida, ENTONCES EL SISTEMA responde con error 400 y no modifica el pedido.
- RF-7: CUANDO cambia el estado, EL SISTEMA registra en `HistorialEstado` el estado anterior, el nuevo, el usuario y la fecha.
- RF-8: EL SISTEMA permite devolver un pedido de "Control de calidad" a "En preparación" cuando se detecta un defecto.

### Descuento de insumos por BOM
- RF-9: CUANDO el pedido pasa a "En preparación", EL SISTEMA descuenta del inventario los insumos de la receta multiplicados por la cantidad de cada producto.
- RF-10: SI algún insumo no alcanza, ENTONCES EL SISTEMA cancela la operación, no cambia el estado y devuelve el detalle de los insumos faltantes.
- RF-11: EL SISTEMA registra cada descuento como movimiento de tipo "consumo" asociado al pedido.
- RF-12: EL SISTEMA descuenta los insumos una sola vez por pedido, aunque se repita la transición.

### Despacho y confirmación
- RF-13: CUANDO se crea un despacho para un pedido en estado "Listo", EL SISTEMA guarda la dirección de entrega; SI el pedido no está "Listo", ENTONCES rechaza la operación.
- RF-14: SI se intenta confirmar la entrega sin firma, sin comprobante o sin receptor, ENTONCES EL SISTEMA rechaza la operación con un mensaje claro.
- RF-15: CUANDO se confirma la entrega con firma o comprobante, EL SISTEMA guarda la fecha, el receptor y la evidencia, y deja el pedido en "Entregado" de forma atómica.
- RF-16: EL SISTEMA muestra en el detalle del pedido su historial completo de estados.
- RF-17: SI un pedido ya tiene los insumos descontados, ENTONCES EL SISTEMA no permite editar sus detalles ni eliminarlo.
- RF-18: EL SISTEMA aplica los permisos por rol tanto en las páginas HTML como en la API.

## Requisitos no funcionales
- RNF-1: Interfaz responsiva en español, usable desde móvil.
- RNF-2: El sitio público (landing, quiénes somos, servicios y contacto) es accesible sin sesión; el panel de gestión, el Kanban, el inventario, los despachos y la API exigen sesión y aplican permisos por rol.
- RNF-3: Fechas en zona horaria `America/Santiago`.
- RNF-4: Base de datos PostgreSQL en la instancia EC2.

## Casos límite
- Pedido sin detalles o con cantidad 0.
- Producto sin receta definida (no descuenta insumos).
- Dos pedidos que consumen el mismo insumo el mismo día.
- Despacho confirmado dos veces.
- Insumo con stock exactamente igual al requerido (debe permitir la operación).

## Fuera de alcance
- Pago en línea y facturación electrónica.
- Notificaciones por correo o WhatsApp.
- Aplicación móvil nativa.

## Criterios de finalización
- Todas las páginas responden 200 y las transiciones inválidas 400 (`smoke_test.py`).
- El stock disminuye exactamente por la cantidad del BOM y queda el movimiento registrado.
- El pedido no puede confirmarse como entregado sin un despacho confirmado con evidencia.
- Los roles incorrectos reciben 403 en la API y un pedido con BOM descontado no se edita ni elimina.

## Dudas abiertas
- Ninguna.
