# La API REST queda reservada a administración

La API DRF existía con permisos por rol, pero eso obligaba a mantener dos caminos para las
mismas reglas (HTML y API) y dejaba una superficie que ventas, cocina, calidad y despacho
podían usar sin pasar por la interfaz. Decidimos que la API sea solo para el rol
administrador: el personal operativo y los clientes trabajan con formularios Django
server-side, y cualquier otro rol recibe 403. Se descartó la alternativa de permisos por rol
en la API porque duplicaba validaciones y multiplicaba los puntos donde una regla podía
divergir.
