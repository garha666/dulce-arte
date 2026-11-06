"""Contexto compartido por todos los templates: rol, menú, etiqueta y carrito."""

from .carrito import detalle
from .roles import etiqueta_rol, menu_para, rol_de


def navegacion(request):
    if request is None:
        return {}
    _, _, unidades = detalle(request)
    return {
        "rol": rol_de(request.user),
        "rol_label": etiqueta_rol(request.user),
        "menu": menu_para(request.user),
        "carrito_unidades": unidades,
    }
