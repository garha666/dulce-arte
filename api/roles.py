"""Roles, menús y permisos de navegación de Dulce Arte.

Centraliza qué puede ver cada rol para que las vistas HTML y los templates
no repitan condicionales.
"""

from .models import Perfil

ETIQUETAS_ROL = dict(Perfil.ROLES)

# Roles autorizados por área. Se usan tanto en las vistas HTML como en la API.
ROLES_PRODUCCION = frozenset({"admin", "cocina", "calidad"})
ROLES_PEDIDOS = frozenset({"admin", "ventas"})
ROLES_DESPACHO = frozenset({"admin", "despacho"})
ROLES_INTERNOS = frozenset({"admin", "ventas", "cocina", "calidad", "despacho"})

# Cada ítem: (nombre de URL, texto del menú)
MENUS = {
    "admin": [
        ("home", "Panel"),
        ("pedidos", "Pedidos"),
        ("kanban", "Cocina"),
        ("inventario", "Insumos"),
        ("despachos", "Despachos"),
        ("tienda", "Tienda"),
    ],
    "ventas": [
        ("home", "Panel"),
        ("pedidos", "Pedidos"),
        ("tienda", "Tienda"),
        ("contacto", "Contacto"),
    ],
    "cocina": [
        ("home", "Panel"),
        ("kanban", "Cocina"),
        ("inventario", "Insumos"),
        ("pedidos", "Pedidos"),
    ],
    "calidad": [
        ("home", "Panel"),
        ("kanban", "Cocina"),
        ("inventario", "Insumos"),
        ("pedidos", "Pedidos"),
    ],
    "despacho": [
        ("home", "Panel"),
        ("despachos", "Despachos"),
        ("pedidos", "Pedidos"),
    ],
    "cliente": [
        ("tienda", "Tienda"),
        ("mis_pedidos", "Mis pedidos"),
        ("seguimiento", "Seguir pedido"),
    ],
}


def rol_de(user):
    """Devuelve el rol efectivo del usuario (o None si no inició sesión)."""
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser or user.is_staff:
        return "admin"
    perfil = getattr(user, "perfil", None)
    return perfil.rol if perfil else "cliente"


def etiqueta_rol(user):
    rol = rol_de(user)
    return ETIQUETAS_ROL.get(rol, "")


def menu_para(user):
    """Ítems del menú que corresponden al rol del usuario."""
    return MENUS.get(rol_de(user), [])


def puede(user, *roles):
    """True si el rol del usuario está dentro de los roles permitidos."""
    return rol_de(user) in roles
