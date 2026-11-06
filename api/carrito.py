"""Carrito de compras en sesión (sin cuentas obligatorias).

Se guarda como {producto_id: {"cantidad": n, "personalizacion": texto}}.
El precio nunca se guarda en sesión: siempre se lee del catálogo actual.
"""

from decimal import Decimal

from .models import Producto

CLAVE = "carrito"


def _datos(request):
    return request.session.setdefault(CLAVE, {})


def agregar(request, producto, cantidad=1, personalizacion=""):
    carrito = _datos(request)
    clave = str(producto.pk)
    actual = carrito.get(clave, {"cantidad": 0, "personalizacion": ""})
    actual["cantidad"] = min(actual.get("cantidad", 0) + max(int(cantidad), 1), 50)
    if personalizacion:
        actual["personalizacion"] = personalizacion[:500]
    carrito[clave] = actual
    request.session[CLAVE] = carrito
    request.session.modified = True


def actualizar(request, producto_id, cantidad):
    carrito = _datos(request)
    clave = str(producto_id)
    if clave not in carrito:
        return
    cantidad = int(cantidad)
    if cantidad <= 0:
        carrito.pop(clave, None)
    else:
        carrito[clave]["cantidad"] = min(cantidad, 50)
    request.session[CLAVE] = carrito
    request.session.modified = True


def quitar(request, producto_id):
    carrito = _datos(request)
    carrito.pop(str(producto_id), None)
    request.session[CLAVE] = carrito
    request.session.modified = True


def vaciar(request):
    request.session[CLAVE] = {}
    request.session.modified = True


def detalle(request):
    """Devuelve (líneas, total, unidades) con precios frescos del catálogo."""
    carrito = _datos(request)
    productos = {
        str(p.pk): p
        for p in Producto.objects.filter(
            pk__in=[int(k) for k in carrito.keys() if str(k).isdigit()],
            activo=True,
        )
    }

    lineas = []
    total = Decimal("0")
    unidades = 0
    for clave, datos in list(carrito.items()):
        producto = productos.get(str(clave))
        if not producto:
            continue
        cantidad = int(datos.get("cantidad", 1))
        subtotal = producto.precio_base * cantidad
        total += subtotal
        unidades += cantidad
        lineas.append(
            {
                "producto": producto,
                "cantidad": cantidad,
                "personalizacion": datos.get("personalizacion", ""),
                "subtotal": subtotal,
            }
        )
    return lineas, total, unidades


def esta_vacio(request):
    return not _datos(request)
