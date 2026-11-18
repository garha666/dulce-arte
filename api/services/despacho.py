"""Servicio de despacho de pedidos.

Extraído de ``despacho_crear`` para separar la lógica de negocio
de la capa de presentación (vista).
"""

from django.db import transaction


def crear_despacho(request, form):
    """Crea un despacho y pasa el pedido asociado a estado Despachado.

    Args:
        request: HttpRequest con el usuario autenticado (admin/despacho).
        form: DespachoForm ya validado (is_valid() == True).

    Returns:
        Despacho creado.

    Raises:
        ValidationError: si el despacho no es válido o el pedido no puede
            pasar a despachado.
    """
    with transaction.atomic():
        despacho = form.save()
        despacho.full_clean()
        despacho.save()
        despacho.pedido.cambiar_estado(
            "despachado",
            usuario=request.user,
            comentario="Pedido asignado a reparto.",
        )
    return despacho
