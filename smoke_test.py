"""Prueba rápida de humo: páginas, tienda, API administrativa y reglas de negocio.

No deja datos: las pruebas de flujo corren dentro de una transacción con rollback.
"""

import os
from datetime import timedelta
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "drf.settings")
django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.core.exceptions import ValidationError  # noqa: E402
from django.db import transaction  # noqa: E402
from django.test import Client  # noqa: E402
from django.utils import timezone  # noqa: E402

from api.models import Cliente, Insumo, Pago, Pedido, PedidoDetalle, Producto  # noqa: E402


def revisar(ruta, esperado, cliente, etiqueta=""):
    respuesta = cliente.get(ruta)
    print(f"{etiqueta or ruta:34} -> {respuesta.status_code}")
    if respuesta.status_code != esperado:
        raise SystemExit(
            f"{etiqueta or ruta} respondió {respuesta.status_code}, se esperaba {esperado}."
        )


publico = Client(SERVER_NAME="localhost")
producto = Producto.objects.filter(activo=True).first()
if not producto:
    raise SystemExit("No hay productos activos. Ejecuta python seed_data.py.")

print("== Sitio público ==")
for ruta in ["/", "/health/", "/tienda/", f"/tienda/{producto.pk}/", "/seguimiento/", "/registro/", "/carrito/", "/servicios/", "/contacto/"]:
    revisar(ruta, 200, publico)

admin = User.objects.filter(username="admin").first()
if not admin or not admin.check_password("Dulce2026!"):
    raise SystemExit("Falta el usuario admin. Ejecuta python seed_data.py.")

interno = Client(SERVER_NAME="localhost")
if not interno.login(username="admin", password="Dulce2026!"):
    raise SystemExit("No se pudo iniciar sesión como admin.")

print("\n== Panel interno y API (admin) ==")
for ruta in ["/kanban/", "/pedidos/", "/mostrador/", "/inventario/", "/despachos/", "/equipo/", "/api/", "/api/pedidos/"]:
    revisar(ruta, 200, interno)

print("\n== La API queda cerrada para roles operativos ==")
ventas = Client(SERVER_NAME="localhost")
ventas.login(username="ventas", password="Dulce2026!")
revisar("/api/pedidos/", 403, ventas, "ventas -> API")
revisar("/mostrador/", 200, ventas, "ventas -> mostrador")

cocina = Client(SERVER_NAME="localhost")
cocina.login(username="cocina", password="Dulce2026!")
revisar("/api/pedidos/", 403, cocina, "cocina -> API")
revisar("/mostrador/", 302, cocina, "cocina -> mostrador")

print("\n== Cliente de la tienda ==")
cliente_web = Client(SERVER_NAME="localhost")
if not cliente_web.login(username="cliente", password="Cliente2026!"):
    raise SystemExit("Falta el cliente demo. Ejecuta python seed_data.py.")
revisar("/tienda/", 200, cliente_web, "cliente -> tienda")
revisar("/mis-pedidos/", 200, cliente_web, "cliente -> mis pedidos")
revisar("/api/productos/", 403, cliente_web, "cliente -> API")

print("\n== Reglas de negocio (con rollback) ==")
cliente = Cliente.objects.filter(nombre__startswith="María").first()
harina = Insumo.objects.get(nombre="Harina sin polvos")
producto_chocolate = Producto.objects.get(nombre="Torta de chocolate")
antes = harina.stock_actual

try:
    with transaction.atomic():
        pedido = Pedido.objects.create(
            cliente=cliente,
            canal="mostrador",
            modalidad="retiro",
            fecha_entrega=timezone.localtime() + timedelta(days=3),
            creado_por=admin,
        )
        PedidoDetalle.objects.create(
            pedido=pedido, producto=producto_chocolate, cantidad=1
        )
        Pago.objects.create(
            pedido=pedido, monto=Decimal("5000"), metodo="efectivo"
        )

        try:
            pedido.cambiar_estado("preparacion", usuario=admin)
            raise SystemExit("Se permitió preparar sin confirmar el pedido.")
        except ValidationError:
            print("Preparar sin confirmar          -> rechazado (correcto)")

        pedido.cambiar_estado("confirmado", usuario=admin)
        pedido.cambiar_estado("preparacion", usuario=admin)
        harina.refresh_from_db()
        print(f"Confirmado + preparación        -> stock {antes} -> {harina.stock_actual}")
        if harina.stock_actual >= antes:
            raise SystemExit("El BOM no descontó insumos al preparar.")

        pedido.cambiar_estado("cancelado", usuario=admin)
        harina.refresh_from_db()
        print(f"Cancelación repone insumos      -> stock {harina.stock_actual}")
        if harina.stock_actual != antes:
            raise SystemExit("La cancelación no repuso los insumos.")

        transaction.set_rollback(True)
except SystemExit:
    raise

print("\nPrueba de humo completada sin errores.")
