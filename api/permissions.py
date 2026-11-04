"""Permisos por rol para la API de Dulce Arte."""

from rest_framework import permissions


class SoloLecturaOSoloAdministrador(permissions.BasePermission):
    """
    Cualquier usuario autenticado puede consultar (GET/HEAD/OPTIONS).
    Solo los administradores (is_staff) pueden crear, editar o eliminar.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff


class PuedeGestionarProduccion(permissions.BasePermission):
    """Solo cocina, control de calidad y administradores mueven el Kanban."""

    ROLES_PERMITIDOS = {"admin", "cocina", "calidad"}

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_staff:
            return True
        perfil = getattr(user, "perfil", None)
        return bool(perfil and perfil.rol in self.ROLES_PERMITIDOS)
