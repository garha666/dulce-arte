# Dulce Arte

Contexto de una pastelería artesanal que vende pedidos personalizados con agenda limitada,
produce contra receta y entrega con evidencia. El lenguaje distingue la venta (pedido y pago)
de la operación (producción, insumos y despacho).

## Venta y clientes

**Cliente**:
Persona u organización que compra en la tienda, tenga o no una cuenta en el sitio.
_Avoid_: Usuario, comprador, consumidor

**Cuenta de cliente**:
Acceso con usuario y contraseña que vincula a una persona con su ficha de cliente.
_Avoid_: Perfil, login

**Pedido**:
Compromiso de elaborar y entregar productos en una fecha y modalidad acordadas.
_Avoid_: Orden, compra, cotización

**Cotización**:
Propuesta de precio y fecha que antecede al pedido; en el sistema el pedido ya nace con precio.
_Avoid_: Presupuesto, pedido

**Canal**:
Origen comercial del pedido: tienda en línea, mostrador o teléfono.
_Avoid_: Medio, fuente

**Modalidad**:
Forma de entrega elegida: retiro en tienda o despacho a domicilio.
_Avoid_: Tipo de entrega, envío

**Anticipo**:
Monto que el cliente paga antes de que el pedido entre a producción.
_Avoid_: Abono, seña, depósito

**Pago**:
Registro de dinero efectivamente recibido, con su método, fecha y responsable.
_Avoid_: Transacción, cobro

**Saldo**:
Diferencia entre el total del pedido y lo efectivamente pagado.
_Avoid_: Deuda, restante

**Estado de pago**:
Situación derivada de los pagos: pendiente, parcial o pagado.
_Avoid_: Estado de cuenta, situación

**Seguimiento**:
Consulta pública del avance de un pedido mediante su código o su token.
_Avoid_: Tracking, rastreo

## Catálogo y producción

**Producto**:
Artículo del catálogo que se elabora a pedido, con precio base y porciones.
_Avoid_: Ítem, artículo, SKU

**Categoría de producto**:
Agrupación comercial del catálogo (tortas, postres, mesas dulces).
_Avoid_: Tipo, familia

**Insumo**:
Materia prima o material de empaque que se consume al producir.
_Avoid_: Material, ingrediente, stock

**Receta**:
Lista de insumos y cantidades necesarias para producir una unidad de un producto.
_Avoid_: BOM, fórmula, composición

**Disponibilidad**:
Cantidad de unidades de un producto que se pueden producir con el stock actual.
_Avoid_: Stock, existencias

**Consumo**:
Salida de insumos del inventario provocada por un pedido que entra a producción.
_Avoid_: Descuento, merma, salida

**Reposición**:
Devolución de insumos al inventario cuando un pedido se cancela después de producir.
_Avoid_: Reembolso, devolución

## Agenda y entrega

**Agenda**:
Fecha y hora comprometidas para entregar o retirar un pedido.
_Avoid_: Horario, reserva

**Anticipación mínima**:
Tiempo mínimo entre la compra y la entrega; para pedidos web es de 48 horas.
_Avoid_: Lead time, plazo

**Cupo diario**:
Cantidad máxima de pedidos no cancelados que se pueden agendar en un día.
_Avoid_: Capacidad, límite

**Retiro**:
Entrega en la tienda, cerrada registrando quién retira el pedido.
_Avoid_: Pickup, recogida

**Despacho**:
Entrega a domicilio mediante una ruta asignada a un repartidor.
_Avoid_: Envío, delivery

**Evidencia de entrega**:
Firma digital o comprobante fotográfico que confirma que el pedido fue recibido.
_Avoid_: Comprobante, respaldo

## Operación interna

**Panel interno**:
Conjunto de pantallas server-side para ventas, cocina, calidad y despacho.
_Avoid_: Backoffice, dashboard, administración

**Tienda**:
Sitio público de catálogo, carrito, checkout, seguimiento y cuenta de cliente.
_Avoid_: E-commerce, frontend

**API administrativa**:
Interfaz REST reservada al rol administrador para integraciones y automatizaciones.
_Avoid_: API pública, API de clientes
