"""API REST — solo administración (Viewsets DRF)."""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import (
    Cliente,
    Despacho,
    Insumo,
    MensajeContacto,
    MovimientoInsumo,
    Pago,
    Pedido,
    PedidoDetalle,
    Producto,
)
from ..permissions import EsAdministrador
from ..serializers import (
    ClienteSerializer,
    DespachoSerializer,
    InsumoSerializer,
    MensajeContactoSerializer,
    MovimientoInsumoSerializer,
    PagoSerializer,
    PedidoSerializer,
    ProductoSerializer,
)

from django.core.exceptions import ValidationError as DjangoValidationError


class PedidoViewSet(viewsets.ModelViewSet):
    """CRUD de pedidos + acciones del tablero, solo para administración."""

    queryset = Pedido.objects.select_related("cliente").prefetch_related(
        "detalles__producto", "historial", "pagos"
    )
    serializer_class = PedidoSerializer
    permission_classes = [EsAdministrador]

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
    permission_classes = [EsAdministrador]
    search_fields = ("nombre", "telefono", "email")


class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.select_related("categoria").prefetch_related(
        "ingredientes__insumo"
    )
    serializer_class = ProductoSerializer
    permission_classes = [EsAdministrador]
    search_fields = ("nombre", "descripcion")


class InsumoViewSet(viewsets.ModelViewSet):
    queryset = Insumo.objects.select_related("categoria")
    serializer_class = InsumoSerializer
    permission_classes = [EsAdministrador]
    search_fields = ("nombre",)
    filterset_fields = ("categoria", "unidad", "perecible")


class DespachoViewSet(viewsets.ModelViewSet):
    queryset = Despacho.objects.select_related("pedido", "repartidor")
    serializer_class = DespachoSerializer
    permission_classes = [EsAdministrador]
    search_fields = ("pedido__codigo", "direccion", "receptor_nombre")

    def destroy(self, request, *args, **kwargs):
        despacho = self.get_object()
        if despacho.confirmado:
            return Response(
                {"detail": "No se puede eliminar un despacho ya confirmado."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.select_related("pedido", "registrado_por")
    serializer_class = PagoSerializer
    permission_classes = [EsAdministrador]
    filterset_fields = ("pedido", "metodo", "tipo")


class MovimientoInsumoViewSet(viewsets.ReadOnlyModelViewSet):
    """Solo lectura: los movimientos son evidencia de auditoría del BOM."""

    queryset = MovimientoInsumo.objects.select_related("insumo", "pedido")
    serializer_class = MovimientoInsumoSerializer
    permission_classes = [EsAdministrador]
    filterset_fields = ("tipo", "insumo", "pedido")
