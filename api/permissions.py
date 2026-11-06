"""Permisos de la API de Dulce Arte.

Decisión de arquitectura: la API REST queda reservada al rol administrador.
El personal operativo (ventas, cocina, calidad, despacho) y los clientes
trabajan únicamente con las páginas HTML del sitio, que aplican sus propias
reglas de rol. Así nadie puede saltarse la interfaz llamando `/api/`.
"""

from rest_framework import permissions

from .roles import rol_de


class EsAdministrador(permissions.BasePermission):
    """Solo el rol administrador puede leer o escribir la API."""

    message = "La API está reservada al rol administrador."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and rol_de(request.user) == "admin"
        )
