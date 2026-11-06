# El flujo incorpora `confirmado` y usa `despachado` de verdad

Antes, un pedido pasaba de `recibido` a `preparacion` sin ninguna señal comercial, y el estado
`despachado` se saltaba al confirmar la entrega. Decidimos que producción no arranque hasta
que ventas confirme el pedido con el anticipo registrado, y que crear una ruta deje el pedido
en `despachado` mientras la evidencia lo cierra en `entregado`. Se descartó mantener el salto
directo porque consumía insumos de pedidos que nunca se habían pagado y dejaba sin estado real
el tiempo en reparto.
