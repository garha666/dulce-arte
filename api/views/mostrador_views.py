"""Venta directa de mostrador (vitrina + cobro inmediato)."""

from decimal import Decimal
from django.contrib import messages
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from urllib.parse import urlencode

from .. import mostrador
from ..forms import VentaMostradorForm
from ..models import Cliente, Pedido, PedidoDetalle, Pago, Producto
from .panel_views import rol_requerido


def _volver_mostrador(request):
    """Vuelve a la vitrina conservando la búsqueda del vendedor."""
    busqueda = (request.POST.get("q") or "").strip()
    url = reverse("mostrador")
    return f"{url}?{urlencode({'q': busqueda})}" if busqueda else url


@rol_requerido("admin", "ventas")
def mostrador_page(request):
    """Vitrina del vendedor: buscar productos, ver stock y armar la venta."""
    busqueda = request.GET.get("q", "").strip()
    productos = (
        Producto.objects.filter(activo=True)
        .select_related("categoria")
        .prefetch_related("ingredientes__insumo")
        .order_by("nombre")
    )
    if busqueda:
        productos = productos.filter(
            Q(nombre__icontains=busqueda)
            | Q(descripcion__icontains=busqueda)
            | Q(categoria__nombre__icontains=busqueda)
        )

    lineas, total, unidades = mostrador.detalle(request)
    return render(
        request,
        "mostrador.html",
        {
            "productos": productos[:60],
            "busqueda": busqueda,
            "lineas": lineas,
            "total": total,
            "unidades": unidades,
            "form": VentaMostradorForm(
                initial={"monto": total, "tipo": "retiro"}
            ),
        },
    )


@rol_requerido("admin", "ventas")
@require_POST
def mostrador_agregar(request):
    producto = get_object_or_404(
        Producto, pk=request.POST.get("producto"), activo=True
    )
    try:
        cantidad = max(int(request.POST.get("cantidad", 1)), 1)
    except (TypeError, ValueError):
        cantidad = 1

    disponibles = producto.unidades_disponibles
    if disponibles is not None:
        total = mostrador.cantidad(request, producto.pk) + cantidad
        if total > disponibles:
            messages.error(
                request,
                f"{producto.nombre}: solo hay {disponibles} unidad"
                f"{'es' if disponibles != 1 else ''} disponible"
                f"{'s' if disponibles != 1 else ''} con el stock actual.",
            )
            return redirect(_volver_mostrador(request))

    mostrador.agregar(request, producto, cantidad)
    messages.success(
        request, f"{producto.nombre} agregado a la venta ({cantidad})."
    )
    return redirect(_volver_mostrador(request))


@rol_requerido("admin", "ventas")
@require_POST
def mostrador_quitar(request, pk):
    mostrador.quitar(request, pk)
    return redirect("mostrador")


@rol_requerido("admin", "ventas")
@require_POST
def mostrador_vaciar(request):
    mostrador.vaciar(request)
    messages.info(request, "Venta de mostrador vaciada.")
    return redirect("mostrador")


@rol_requerido("admin", "ventas")
@require_POST
def mostrador_confirmar(request):
    """Cierra la venta: crea el pedido, cobra y descuenta insumos una sola vez."""
    lineas, total, _ = mostrador.detalle(request)
    if not lineas:
        messages.error(request, "Agrega al menos un producto a la venta.")
        return redirect("mostrador")

    form = VentaMostradorForm(request.POST)
    if not form.is_valid():
        for errores in form.errors.values():
            for error in errores:
                messages.error(request, error)
        return redirect("mostrador")

    datos = form.cleaned_data
    modalidad = "retiro" if datos["tipo"] == "retiro" else "despacho"
    direccion = (datos.get("direccion_entrega") or "").strip()

    try:
        with transaction.atomic():
            cliente = datos.get("cliente")
            if cliente is None:
                nombre = datos["nuevo_nombre"].strip()
                telefono = datos["nuevo_telefono"].strip()
                cliente = Cliente.objects.filter(telefono=telefono).first()
                if cliente is None:
                    cliente = Cliente.objects.create(
                        nombre=nombre,
                        telefono=telefono,
                        email=(datos.get("nuevo_email") or "").strip(),
                        direccion=(datos.get("nueva_direccion") or "").strip(),
                    )

            retirado_por = (datos.get("retirado_por") or "").strip()
            if modalidad == "retiro":
                retirado_por = retirado_por or cliente.nombre

            pedido = Pedido(
                cliente=cliente,
                canal="mostrador",
                modalidad=modalidad,
                estado="recibido",
                fecha_entrega=timezone.now(),
                direccion_entrega=direccion,
                telefono_contacto=cliente.telefono,
                descripcion_diseno="Venta directa de mostrador",
                observaciones=(datos.get("observaciones") or "").strip(),
                retirado_por=retirado_por if modalidad == "retiro" else "",
                creado_por=request.user,
                venta_directa=True,
            )
            pedido.save()
            for linea in lineas:
                PedidoDetalle.objects.create(
                    pedido=pedido,
                    producto=linea["producto"],
                    cantidad=linea["cantidad"],
                )

            monto = datos.get("monto") or Decimal("0")
            if monto > 0:
                pago = Pago(
                    pedido=pedido,
                    monto=monto,
                    metodo=datos["metodo"],
                    tipo="completo" if monto >= pedido.total else "anticipo",
                    registrado_por=request.user,
                )
                pago.full_clean()
                pago.save()

            pedido.cambiar_estado(
                "entregado" if modalidad == "retiro" else "despachado",
                usuario=request.user,
                comentario="Venta directa registrada en mostrador.",
                venta_directa=True,
            )
    except DjangoValidationError as error:
        for mensaje in error.messages:
            messages.error(request, mensaje)
        return redirect("mostrador")

    mostrador.vaciar(request)
    messages.success(
        request,
        f"Venta {pedido.codigo} registrada por ${pedido.total:,.0f}. "
        f"Stock descontado y pedido {pedido.get_estado_display().lower()}.",
    )
    return redirect("pedido_detalle", pk=pedido.pk)
