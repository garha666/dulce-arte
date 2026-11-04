"""Prueba rápida de humo: páginas, API y regla del Kanban/BOM."""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "drf.settings")
django.setup()

from decimal import Decimal  # noqa: E402

from django.test import Client  # noqa: E402

from api.models import Insumo, MovimientoInsumo, Pedido  # noqa: E402

cliente = Client(SERVER_NAME="localhost")

print("Login:", cliente.login(username="admin", password="Dulce2026!"))

rutas = [
    "/", "/kanban/", "/pedidos/", "/inventario/", "/despachos/",
    "/quienes-somos/", "/servicios/", "/contacto/", "/api/", "/api/pedidos/",
]
for ruta in rutas:
    respuesta = cliente.get(ruta)
    print(f"{ruta:22} -> {respuesta.status_code}")

# ---- Regla de negocio: pasar a 'preparacion' descuenta insumos (BOM) ----
pedido = Pedido.objects.filter(estado="recibido").first()
if pedido:
    harina = Insumo.objects.get(nombre="Harina sin polvos")
    antes = harina.stock_actual

    respuesta = cliente.post(
        f"/api/pedidos/{pedido.pk}/cambiar_estado/",
        data={"estado": "preparacion"},
        content_type="application/json",
    )
    harina.refresh_from_db()
    pedido.refresh_from_db()

    print(f"\nCambio de estado -> HTTP {respuesta.status_code}")
    print(f"Estado nuevo: {pedido.estado} | insumos descontados: {pedido.insumos_descontados}")
    print(f"Stock harina: {antes} -> {harina.stock_actual}")
    print(f"Movimientos de consumo: {MovimientoInsumo.objects.filter(tipo='consumo').count()}")

    # Transición inválida: debe responder 400
    invalida = cliente.post(
        f"/api/pedidos/{pedido.pk}/cambiar_estado/",
        data={"estado": "entregado"},
        content_type="application/json",
    )
    print(f"Transición inválida -> HTTP {invalida.status_code} ({invalida.json()})")
else:
    print("No hay pedidos en estado 'recibido' para probar.")
