"""Rutas de la app api: tienda, panel interno y API administrativa."""

from django.urls import include, path
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r"pedidos", views.PedidoViewSet)
router.register(r"clientes", views.ClienteViewSet)
router.register(r"productos", views.ProductoViewSet)
router.register(r"insumos", views.InsumoViewSet)
router.register(r"despachos", views.DespachoViewSet)
router.register(r"pagos", views.PagoViewSet)
router.register(r"movimientos", views.MovimientoInsumoViewSet)

urlpatterns = [
    # ------------------------------------------------------------- sesión
    path("health/", views.health, name="health"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("registro/", views.registro, name="registro"),
    # -------------------------------------------------------------- tienda
    path("", views.home, name="home"),
    path("tienda/", views.tienda, name="tienda"),
    path("tienda/<int:pk>/", views.producto_detalle, name="producto_detalle"),
    path("carrito/", views.carrito_ver, name="carrito"),
    path("carrito/agregar/<int:pk>/", views.carrito_agregar, name="carrito_agregar"),
    path(
        "carrito/actualizar/<int:pk>/",
        views.carrito_actualizar,
        name="carrito_actualizar",
    ),
    path("carrito/quitar/<int:pk>/", views.carrito_quitar, name="carrito_quitar"),
    path("checkout/", views.checkout, name="checkout"),
    path("seguimiento/", views.seguimiento, name="seguimiento"),
    path(
        "seguimiento/<str:token>/",
        views.seguimiento_detalle,
        name="seguimiento_detalle",
    ),
    path("mis-pedidos/", views.mis_pedidos, name="mis_pedidos"),
    # ------------------------------------------------------ panel interno
    path("kanban/", views.kanban_page, name="kanban"),
    path("pedidos/", views.pedidos_page, name="pedidos"),
    path("pedidos/nuevo/", views.pedido_crear, name="pedido_crear"),
    path("pedidos/<int:pk>/", views.pedido_detalle_page, name="pedido_detalle"),
    path(
        "pedidos/<int:pk>/editar/",
        views.pedido_editar,
        name="pedido_editar",
    ),
    path(
        "pedidos/<int:pk>/estado/",
        views.pedido_cambiar_estado,
        name="pedido_cambiar_estado",
    ),
    path(
        "pedidos/<int:pk>/pago/",
        views.pedido_registrar_pago,
        name="pedido_registrar_pago",
    ),
    path("pedidos/<int:pk>/retiro/", views.retiro_confirmar, name="retiro_confirmar"),
    path("inventario/", views.inventario_page, name="inventario"),
    path("equipo/", views.equipo_page, name="equipo"),
    path(
        "equipo/usuarios/nuevo/",
        views.equipo_crear_usuario,
        name="equipo_crear_usuario",
    ),
    path(
        "equipo/clientes/nuevo/",
        views.equipo_crear_cliente,
        name="equipo_crear_cliente",
    ),
    path("despachos/", views.despachos_page, name="despachos"),
    path("despachos/crear/", views.despacho_crear, name="despacho_crear"),
    path(
        "despachos/<int:pk>/confirmar/",
        views.despacho_confirmar,
        name="despacho_confirmar",
    ),
    # ------------------------------------------------------ sitio público
    path("quienes-somos/", views.quienes_somos, name="quienes_somos"),
    path("servicios/", views.servicios, name="servicios"),
    path("contacto/", views.contacto, name="contacto"),
    # ------------------------------------------- API reservada a admin
    path("api/", include(router.urls)),
]
