"""Vistas de Dulce Arte: API (DRF) + páginas HTML con templates."""

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.core.exceptions import ValidationError as DjangoValidationError

from .models import (
    Cliente,
    Despacho,
    Insumo,
    MensajeContacto,
    MovimientoInsumo,
    Pedido,
    Producto,
)
from .permissions import PuedeGestionarProduccion, SoloLecturaOSoloAdministrador
from .serializers import (
    ClienteSerializer,
    DespachoSerializer,
    InsumoSerializer,
    MensajeContactoSerializer,
    MovimientoInsumoSerializer,
    PedidoSerializer,
    ProductoSerializer,
)

# =========================================================================== #
#  API REST
# =========================================================================== #


class PedidoViewSet(viewsets.ModelViewSet):
    """CRUD de pedidos + acciones del tablero Kanban."""

    queryset = Pedido.objects.select_related("cliente").prefetch_related(
        "detalles__producto", "historial"
    )
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        estado = self.request.query_params.get("estado")
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, PuedeGestionarProduccion],
    )
    def cambiar_estado(self, request, pk=None):
        """Mueve el pedido en el Kanban validando el flujo y descontando BOM."""
        pedido = self.get_object()
        nuevo_estado = request.data.get("estado")
        comentario = request.data.get("comentario", "")
        try:
            pedido.cambiar_estado(
                nuevo_estado, usuario=request.user, comentario=comentario
            )
        except DjangoValidationError as error:
            return Response(
                {"detail": error.messages}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(self.get_serializer(pedido).data)

    @action(detail=True, methods=["post"])
    def descontar_insumos(self, request, pk=None):
        """Fuerza el descuento de insumos (si aún no se ha hecho)."""
        pedido = self.get_object()
        try:
            pedido.descontar_insumos(usuario=request.user)
        except DjangoValidationError as error:
            return Response(
                {"detail": error.messages}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(self.get_serializer(pedido).data)


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all().order_by("nombre")
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated, SoloLecturaOSoloAdministrador]
    search_fields = ("nombre", "telefono", "email")


class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.prefetch_related("ingredientes__insumo")
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated, SoloLecturaOSoloAdministrador]
    search_fields = ("nombre", "descripcion")


class InsumoViewSet(viewsets.ModelViewSet):
    queryset = Insumo.objects.select_related("categoria")
    serializer_class = InsumoSerializer
    permission_classes = [IsAuthenticated, SoloLecturaOSoloAdministrador]
    search_fields = ("nombre",)
    filterset_fields = ("categoria", "unidad", "perecible")


class DespachoViewSet(viewsets.ModelViewSet):
    queryset = Despacho.objects.select_related("pedido", "repartidor")
    serializer_class = DespachoSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ("pedido__codigo", "direccion", "receptor_nombre")


class MovimientoInsumoViewSet(viewsets.ReadOnlyModelViewSet):
    """Solo lectura: los movimientos son evidencia de auditoría del BOM."""

    queryset = MovimientoInsumo.objects.select_related("insumo", "pedido")
    serializer_class = MovimientoInsumoSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ("tipo", "insumo", "pedido")


# =========================================================================== #
#  Páginas HTML (templates)
# =========================================================================== #


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(request.GET.get("next") or "home")
        messages.error(request, "Usuario o contraseña incorrectos.")
    return render(request, "login.html")


def logout_view(request):
    logout(request)
    messages.info(request, "Sesión cerrada correctamente.")
    return redirect("login")


@login_required
def home(request):
    hoy = timezone.localdate()
    pedidos = Pedido.objects.all()

    contexto = {
        "total_pedidos": pedidos.count(),
        "pedidos_semana": pedidos.filter(fecha_pedido__date=hoy).count(),
        "pendientes": pedidos.exclude(estado__in=["entregado", "cancelado"]).count(),
        "por_estado": {
            etiqueta: pedidos.filter(estado=clave).count()
            for clave, etiqueta in Pedido.ESTADOS
        },
        "stock_bajo": Insumo.objects.filter(stock_actual__lte=F("stock_minimo")).count(),
        "insumos_bajo": [i for i in Insumo.objects.all() if i.stock_bajo],
        "proximos": pedidos.exclude(estado__in=["entregado", "cancelado"]).order_by(
            "fecha_entrega"
        )[:6],
        "ventas_total": sum(
            (p.total for p in pedidos.exclude(estado="cancelado")), start=0
        ),
        "ultimos_movimientos": MovimientoInsumo.objects.select_related("insumo")[:5],
    }
    return render(request, "home.html", contexto)


@login_required
def kanban_page(request):
    columnas = []
    for clave, etiqueta in Pedido.ESTADOS:
        if clave in ("despachado", "cancelado"):
            continue
        columnas.append(
            {
                "clave": clave,
                "etiqueta": etiqueta,
                "pedidos": Pedido.objects.filter(estado=clave)
                .select_related("cliente")
                .order_by("fecha_entrega"),
            }
        )
    return render(request, "kanban.html", {"columnas": columnas})


@login_required
def pedidos_page(request):
    return render(
        request,
        "pedidos.html",
        {
            "clientes": Cliente.objects.all(),
            "productos": Producto.objects.filter(activo=True),
        },
    )


@login_required
def inventario_page(request):
    return render(
        request,
        "inventario.html",
        {
            "insumos": Insumo.objects.select_related("categoria").order_by("nombre"),
            "productos": Producto.objects.prefetch_related("ingredientes__insumo"),
        },
    )


@login_required
def despachos_page(request):
    return render(
        request,
        "despachos.html",
        {
            "despachos": Despacho.objects.select_related("pedido", "repartidor"),
            "pedidos_listos": Pedido.objects.filter(estado="listo"),
        },
    )


@login_required
def pedido_detalle_page(request, pk):
    pedido = get_object_or_404(
        Pedido.objects.select_related("cliente").prefetch_related(
            "detalles__producto", "historial"
        ),
        pk=pk,
    )
    return render(request, "pedido_detalle.html", {"pedido": pedido})


@login_required
@require_POST
def despacho_crear(request):
    """Crea el despacho de un pedido que ya está en estado 'listo'."""
    pedido = get_object_or_404(Pedido, pk=request.POST.get("pedido"))
    direccion = request.POST.get("direccion", "").strip() or pedido.cliente.direccion

    Despacho.objects.get_or_create(
        pedido=pedido, defaults={"direccion": direccion or "Retiro en tienda"}
    )
    messages.success(request, f"Despacho creado para el pedido {pedido.codigo}.")
    return redirect("despachos")


@login_required
@require_POST
def despacho_confirmar(request, pk):
    """Confirma la entrega con firma digital o comprobante fotográfico."""
    despacho = get_object_or_404(Despacho, pk=pk)
    despacho.receptor_nombre = request.POST.get("receptor_nombre", "").strip()
    despacho.fecha_entrega = timezone.now()
    despacho.observaciones = request.POST.get("observaciones", despacho.observaciones)

    if request.FILES.get("firma"):
        despacho.firma = request.FILES["firma"]
    if request.FILES.get("comprobante"):
        despacho.comprobante = request.FILES["comprobante"]

    try:
        despacho.full_clean()
        despacho.save()
    except DjangoValidationError as error:
        messages.error(request, " ".join(error.messages))
        return redirect("despachos")

    messages.success(
        request, f"Entrega del pedido {despacho.pedido.codigo} confirmada correctamente."
    )
    return redirect("despachos")


def quienes_somos(request):
    return render(request, "quienes_somos.html")


def servicios(request):
    return render(request, "servicios.html")


def contacto(request):
    if request.method == "POST":
        MensajeContacto.objects.create(
            nombre=request.POST.get("nombre", ""),
            email=request.POST.get("email", ""),
            telefono=request.POST.get("telefono", ""),
            mensaje=request.POST.get("mensaje", ""),
        )
        messages.success(
            request, "¡Gracias por escribirnos! Te responderemos a la brevedad."
        )
        return redirect("contacto")
    return render(request, "contacto.html")
