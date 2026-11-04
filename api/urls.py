"""Rutas de la app api: endpoints DRF + páginas HTML."""

from django.urls import include, path
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r"pedidos", views.PedidoViewSet)
router.register(r"clientes", views.ClienteViewSet)
router.register(r"productos", views.ProductoViewSet)
router.register(r"insumos", views.InsumoViewSet)
router.register(r"despachos", views.DespachoViewSet)
router.register(r"movimientos", views.MovimientoInsumoViewSet)

# Páginas del sitio (templates)
urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.home, name="home"),
    path("kanban/", views.kanban_page, name="kanban"),
    path("pedidos/", views.pedidos_page, name="pedidos"),
    path("pedidos/<int:pk>/", views.pedido_detalle_page, name="pedido_detalle"),
    path("inventario/", views.inventario_page, name="inventario"),
    path("despachos/", views.despachos_page, name="despachos"),
    path("despachos/crear/", views.despacho_crear, name="despacho_crear"),
    path("despachos/<int:pk>/confirmar/", views.despacho_confirmar, name="despacho_confirmar"),
    path("quienes-somos/", views.quienes_somos, name="quienes_somos"),
    path("servicios/", views.servicios, name="servicios"),
    path("contacto/", views.contacto, name="contacto"),
    path("api/", include(router.urls)),
]
