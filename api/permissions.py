"""Permisos por rol para la API de Dulce Arte.

La API y las páginas HTML comparten el mismo mapa de roles (`api/roles.py`).
Así evitamos que un usuario pueda saltarse la interfaz llamando la API directo.
"""

from rest_framework import permissions

from .roles import ROLES_DESPACHO, ROLES_PEDIDOS, ROLES_PRODUCCION, rol_de


class RolPermitido(permissions.BasePermission):
    """Base para permisos que dependen del rol efectivo del usuario."""

    roles_permitidos = frozenset()

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and rol_de(request.user) in self.roles_permitidos
        )


class SoloLecturaOSoloAdministrador(permissions.BasePermission):
    """Lectura para usuarios autenticados; escritura solo para administradores."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return rol_de(request.user) == "admin"


class PuedeGestionarProduccion(RolPermitido):
    """Solo cocina, control de calidad y administradores mueven el Kanban."""

    roles_permitidos = ROLES_PRODUCCION


class PuedeGestionarPedidos(RolPermitido):
    """Ventas y administración crean, editan y eliminan pedidos."""

    roles_permitidos = ROLES_PEDIDOS


class PuedeGestionarDespacho(RolPermitido):
    """Despacho y administración gestionan rutas y confirmaciones."""

    roles_permitidos = ROLES_DESPACHO
