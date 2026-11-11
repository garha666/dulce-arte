"""Venta de mostrador en sesión.

El vendedor arma una venta con productos de vitrina y recién al confirmar se
crea el pedido. Igual que el carrito público, nunca se guarda el precio: se lee
del catálogo al mostrar y al cobrar.
"""

from decimal import Decimal

from .models import Producto

CLAVE = "venta_mostrador"
MAXIMO_POR_LINEA = 50


def _datos(request):
    return request.session.setdefault(CLAVE, {})


def agregar(request, producto, cantidad=1):
    datos = _datos(request)
    clave = str(producto.pk)
    actual = datos.get(clave, {"cantidad": 0})
    actual["cantidad"] = min(
        int(actual.get("cantidad", 0)) + max(int(cantidad), 1),
        MAXIMO_POR_LINEA,
    )
    datos[clave] = actual
    request.session[CLAVE] = datos
    request.session.modified = True


def actualizar(request, producto_id, cantidad):
    datos = _datos(request)
    clave = str(producto_id)
    if clave not in datos:
        return
    cantidad = int(cantidad)
    if cantidad <= 0:
        datos.pop(clave, None)
    else:
        datos[clave]["cantidad"] = min(cantidad, MAXIMO_POR_LINEA)
    request.session[CLAVE] = datos
    request.session.modified = True


def quitar(request, producto_id):
    datos = _datos(request)
    datos.pop(str(producto_id), None)
    request.session[CLAVE] = datos
    request.session.modified = True


def cantidad(request, producto_id):
    """Cantidad ya agregada de un producto (0 si no está en la venta)."""
    return int(_datos(request).get(str(producto_id), {}).get("cantidad", 0))


def vaciar(request):
    request.session[CLAVE] = {}
    request.session.modified = True


def detalle(request):
    """Devuelve (líneas, total, unidades) con precios y stock vigentes."""
    datos = _datos(request)
    productos = {
        str(p.pk): p
        for p in Producto.objects.filter(
            pk__in=[int(k) for k in datos.keys() if str(k).isdigit()],
            activo=True,
        ).prefetch_related("ingredientes__insumo")
    }

    lineas = []
    total = Decimal("0")
    unidades = 0
    for clave, item in list(datos.items()):
        producto = productos.get(str(clave))
        if not producto:
            continue
        cantidad = int(item.get("cantidad", 1))
        subtotal = producto.precio_base * cantidad
        total += subtotal
        unidades += cantidad
        lineas.append(
            {
                "producto": producto,
                "cantidad": cantidad,
                "subtotal": subtotal,
                "disponibles": producto.unidades_disponibles,
            }
        )
    return lineas, total, unidades


def esta_vacio(request):
    return not _datos(request)
