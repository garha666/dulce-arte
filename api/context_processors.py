"""Contexto compartido por todos los templates: rol, menú y etiqueta."""

from .roles import etiqueta_rol, menu_para, rol_de


def navegacion(request):
    return {
        "rol": rol_de(request.user),
        "rol_label": etiqueta_rol(request.user),
        "menu": menu_para(request.user),
    }
