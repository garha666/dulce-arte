# El carrito vive en la sesión y siempre lee precios frescos

El carrito se guarda como `{producto_id: cantidad + personalización}` en la sesión, sin crear un
modelo en base de datos ni exigir cuenta. El precio nunca se guarda: cada vez que se muestra o
se cobra, se lee `Producto.precio_base` vigente. Se descartó un `Carrito` persistente porque
agregaba tablas, limpieza de carritos abandonados y un caso más de permisos para una compra que
puede completarse como invitado; el precio histórico solo se congela al crear el `PedidoDetalle`.
