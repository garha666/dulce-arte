# Los pagos son registros manuales, no un campo de anticipo

El pedido guardaba un único `anticipo` como número, sin método, fecha ni responsable, y el
saldo se calculaba restando ese valor. Decidimos crear `Pago` como registro real de cada abono
(efectivo, transferencia o tarjeta) y derivar de ahí `total_pagado`, `estado_pago` y `saldo`,
manteniendo `anticipo` solo como respaldo histórico. Se descartó integrar una pasarela de pago
porque la pastelería cobra por transferencia o en tienda y no emite factura electrónica; el
pago manual deja auditoría sin agregar dependencias externas.
