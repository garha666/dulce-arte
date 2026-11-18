"""Consultas reutilizables de la app.

Evita duplicar la misma búsqueda en varias vistas (tienda, panel, mostrador).
"""

from .models import Cliente


def cliente_de(user):
    """Ficha de cliente vinculada al usuario, si existe."""
    if not user.is_authenticated:
        return None
    return Cliente.objects.filter(user=user).first()
