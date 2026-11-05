"""Vistas de Dulce Arte: API (DRF) + páginas HTML con templates."""

from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    Cliente,
    Despacho,
    Insumo,
    MensajeContacto,
    MovimientoInsumo,
    Pedido,
    Producto,
)
from .permissions import (
    PuedeGestionarDespacho,
    PuedeGestionarPedidos,
    PuedeGestionarProduccion,
    SoloLecturaOSoloAdministrador,
)
from .roles import puede, rol_de
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

    def get_permissions(self):
        """Aplica el rol correcto según la acción solicitada."""
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), PuedeGestionarPedidos()]
        if self.action in ("cambiar_estado", "descontar_insumos"):
            return [IsAuthenticated(), PuedeGestionarProduccion()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        estado = self.request.query_params.get("estado")
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """No se eliminan pedidos que ya consumieron inventario."""
        pedido = self.get_object()
        if pedido.insumos_descontados:
            return Response(
                {
                    "detail": (
                        "No se puede eliminar un pedido con insumos ya "
                        "descontados del inventario."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
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

    def get_permissions(self):
        """Lectura autenticada; escritura solo para despacho y administración."""
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAuthenticated(), PuedeGestionarDespacho()]

    def destroy(self, request, *args, **kwargs):
        """La evidencia de una entrega confirmada no se puede borrar."""
        despacho = self.get_object()
        if despacho.confirmado:
            return Response(
                {"detail": "No se puede eliminar un despacho ya confirmado."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class MovimientoInsumoViewSet(viewsets.ReadOnlyModelViewSet):
    """Solo lectura: los movimientos son evidencia de auditoría del BOM."""

    queryset = MovimientoInsumo.objects.select_related("insumo", "pedido")
    serializer_class = MovimientoInsumoSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ("tipo", "insumo", "pedido")


# =========================================================================== #
#  Páginas HTML (templates)
# =========================================================================== #


def rol_requerido(*roles):
    """Restringe una página a los roles indicados y redirige al panel si no aplica."""

    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(request, *args, **kwargs):
            if not puede(request.user, *roles):
                messages.error(request, "Tu rol no tiene acceso a esa sección.")
                return redirect("home")
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador


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


def home(request):
    """Landing pública para visitantes y panel distinto según el rol."""
    if not request.user.is_authenticated:
        return render(
            request,
            "landing.html",
            {"productos": Producto.objects.filter(activo=True)[:3]},
        )

    rol = rol_de(request.user)
    hoy = timezone.localdate()
    pedidos = Pedido.objects.select_related("cliente")
    activos = pedidos.exclude(estado__in=["entregado", "cancelado"])

    contexto = {
        "hoy": hoy,
        "total_pedidos": pedidos.count(),
        "pendientes": activos.count(),
        "stock_bajo": Insumo.objects.filter(
            stock_actual__lte=F("stock_minimo")
        ).count(),
        "insumos_bajo": [
            insumo
            for insumo in Insumo.objects.select_related("categoria")
            if insumo.stock_bajo
        ],
    }

    if rol == "admin":
        contexto.update(
            {
                "proximos": activos.order_by("fecha_entrega")[:6],
                "ventas_total": sum(
                    (p.total for p in pedidos.exclude(estado="cancelado")), start=0
                ),
                "pedidos_hoy": pedidos.filter(fecha_pedido__date=hoy).count(),
                "ultimos_movimientos": MovimientoInsumo.objects.select_related(
                    "insumo"
                )[:5],
                "por_estado": [
                    (etiqueta, pedidos.filter(estado=clave).count())
                    for clave, etiqueta in Pedido.ESTADOS
                ],
            }
        )
    elif rol == "ventas":
        contexto.update(
            {
                "mis_pedidos": pedidos.filter(creado_por=request.user)[:8],
                "proximos": activos.order_by("fecha_entrega")[:6],
                "ventas_mes": sum(
                    (
                        p.total
                        for p in pedidos.filter(
                            fecha_pedido__year=hoy.year,
                            fecha_pedido__month=hoy.month,
                        ).exclude(estado="cancelado")
                    ),
                    start=0,
                ),
                "clientes_total": Cliente.objects.count(),
                "productos_total": Producto.objects.filter(activo=True).count(),
            }
        )
    elif rol == "cocina":
        contexto.update(
            {
                "en_preparacion": activos.filter(estado="preparacion").order_by(
                    "fecha_entrega"
                ),
                "en_horneado": activos.filter(estado="horneado").order_by(
                    "fecha_entrega"
                ),
                "por_estado": [
                    (etiqueta, pedidos.filter(estado=clave).count())
                    for clave, etiqueta in Pedido.ESTADOS
                    if clave in ("preparacion", "horneado", "calidad", "listo")
                ],
            }
        )
    elif rol == "calidad":
        contexto.update(
            {
                "en_calidad": activos.filter(estado="calidad").order_by(
                    "fecha_entrega"
                ),
                "listos": pedidos.filter(estado="listo").order_by("fecha_entrega"),
            }
        )
    elif rol == "despacho":
        contexto.update(
            {
                "listos": pedidos.filter(estado="listo").order_by("fecha_entrega"),
                "despachos_pendientes": Despacho.objects.select_related(
                    "pedido", "repartidor"
                ).filter(fecha_entrega__isnull=True),
                "entregas_hoy": Despacho.objects.filter(
                    fecha_entrega__date=hoy
                ).select_related("pedido"),
            }
        )

    return render(request, "home.html", contexto)


@rol_requerido("admin", "cocina", "calidad")
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
            "puede_crear": puede(request.user, "admin", "ventas"),
        },
    )


@rol_requerido("admin", "cocina", "calidad")
def inventario_page(request):
    return render(
        request,
        "inventario.html",
        {
            "insumos": Insumo.objects.select_related("categoria").order_by("nombre"),
            "productos": Producto.objects.prefetch_related("ingredientes__insumo"),
        },
    )


@rol_requerido("admin", "despacho")
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


@rol_requerido("admin", "despacho")
@require_POST
def despacho_crear(request):
    """Crea el despacho de un pedido que ya está en estado 'listo'."""
    pedido = get_object_or_404(Pedido, pk=request.POST.get("pedido"))
    if pedido.estado != "listo":
        messages.error(
            request,
            "Solo se puede crear un despacho para un pedido en estado Listo.",
        )
        return redirect("despachos")

    direccion = request.POST.get("direccion", "").strip() or pedido.cliente.direccion
    _, creado = Despacho.objects.get_or_create(
        pedido=pedido, defaults={"direccion": direccion or "Retiro en tienda"}
    )

    if creado:
        messages.success(request, f"Despacho creado para el pedido {pedido.codigo}.")
    else:
        messages.info(
            request, f"El pedido {pedido.codigo} ya tiene un despacho registrado."
        )
    return redirect("despachos")


@rol_requerido("admin", "despacho")
@require_POST
def despacho_confirmar(request, pk):
    """Confirma la entrega con firma digital o comprobante fotográfico."""
    despacho = get_object_or_404(Despacho.objects.select_related("pedido"), pk=pk)

    if despacho.confirmado:
        messages.error(request, "Este despacho ya fue confirmado anteriormente.")
        return redirect("despachos")

    receptor = request.POST.get("receptor_nombre", "").strip()
    if not receptor:
        messages.error(request, "Debes indicar quién recibe la entrega.")
        return redirect("despachos")

    despacho.receptor_nombre = receptor
    despacho.fecha_entrega = timezone.now()
    despacho.observaciones = request.POST.get("observaciones", despacho.observaciones)

    if request.FILES.get("firma"):
        despacho.firma = request.FILES["firma"]
    if request.FILES.get("comprobante"):
        despacho.comprobante = request.FILES["comprobante"]

    try:
        with transaction.atomic():
            despacho.full_clean()
            despacho.save()

            if despacho.pedido.estado != "entregado":
                despacho.pedido.cambiar_estado(
                    "entregado",
                    usuario=request.user,
                    comentario=f"Entrega confirmada del despacho {despacho.pk}.",
                )
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
