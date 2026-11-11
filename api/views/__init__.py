"""Paquete de vistas de Dulce Arte.

Se divide en submódulos por dominio para evitar un views.py monolítico:

- ``util_views.py``: health, login, logout.
- ``tienda_views.py``: tienda pública, carrito, checkout, seguimiento, cuenta.
- ``panel_views.py``: panel interno (pedidos, equipo, kanban, inventario, despachos).
- ``mostrador_views.py``: venta directa de mostrador.
- ``api_views.py``: Viewsets DRF (solo administración).

Se re-exportan todos los símbolos para que ``from . import views`` y
``views.<funcion>`` sigan funcionando sin cambiar ``urls.py``.
"""

from .api_views import (
    ClienteViewSet,
    DespachoViewSet,
    InsumoViewSet,
    MovimientoInsumoViewSet,
    PagoViewSet,
    PedidoViewSet,
    ProductoViewSet,
)
from .mostrador_views import (
    mostrador_agregar,
    mostrador_confirmar,
    mostrador_page,
    mostrador_quitar,
    mostrador_vaciar,
)
from .panel_views import (
    cliente_de,
    despacho_confirmar,
    despacho_crear,
    despachos_page,
    equipo_crear_cliente,
    equipo_crear_usuario,
    equipo_page,
    inventario_page,
    kanban_page,
    pedidos_page,
    pedido_cambiar_estado,
    pedido_crear,
    pedido_detalle_page,
    pedido_editar,
    pedido_registrar_pago,
    rol_requerido,
    retiro_confirmar,
)
from .tienda_views import (
    carrito_actualizar,
    carrito_agregar,
    carrito_quitar,
    carrito_ver,
    checkout,
    contacto,
    home,
    mis_pedidos,
    producto_detalle,
    registro,
    seguimiento,
    seguimiento_detalle,
    tienda,
    quienes_somos,
    servicios,
)
from .util_views import health, login_view, logout_view
