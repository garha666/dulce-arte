"""Servicio de venta directa de mostrador.

Extraído de ``mostrador_confirmar`` para separar la lógica de negocio
de la capa de presentación (vista).
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from ..models import Cliente, Pedido, PedidoDetalle, Pago


def cerrar_venta_mostrador(request, datos, lineas):
    """Cierra una venta de mostrador: crea pedido, paga y descuenta insumos.

    Args:
        request: HttpRequest con el usuario autenticado (admin/ventas).
        datos: dict con los datos limpios de VentaMostradorForm.
        lineas: lista de líneas del carrito de mostrador.

    Returns:
        Pedido creado y cerrado.

    Raises:
        ValidationError: si algo falla en la creación o el cambio de estado.
    """
    modalidad = "retiro" if datos["tipo"] == "retiro" else "despacho"
    direccion = (datos.get("direccion_entrega") or "").strip()

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

    return pedido
