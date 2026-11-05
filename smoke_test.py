"""Prueba rápida de humo: páginas, API y regla del Kanban/BOM."""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "drf.settings")
django.setup()

from django.test import Client  # noqa: E402

from api.models import Insumo, MovimientoInsumo, Pedido  # noqa: E402

cliente = Client(SERVER_NAME="localhost")

login_ok = cliente.login(username="admin", password="Dulce2026!")
print("Login:", login_ok)
if not login_ok:
    raise SystemExit(
        "No se pudo iniciar sesión con admin/Dulce2026!. "
        "Ejecuta python seed_data.py o revisa las credenciales."
    )

rutas = [
    "/", "/kanban/", "/pedidos/", "/inventario/", "/despachos/",
    "/quienes-somos/", "/servicios/", "/contacto/", "/api/", "/api/pedidos/",
]
for ruta in rutas:
    respuesta = cliente.get(ruta)
    print(f"{ruta:22} -> {respuesta.status_code}")
    if respuesta.status_code != 200:
        raise SystemExit(f"La ruta {ruta} respondió {respuesta.status_code}, se esperaba 200.")

# ---- Regla de negocio: pasar a 'preparacion' descuenta insumos (BOM) ----
pedido = Pedido.objects.filter(estado="recibido").first()
if not pedido:
    raise SystemExit(
        "No hay pedidos en estado 'recibido' para probar la transición central. "
        "Ejecuta python seed_data.py o crea un pedido nuevo antes de la prueba."
    )

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

if respuesta.status_code != 200:
    raise SystemExit(f"El cambio de estado respondió {respuesta.status_code}, se esperaba 200.")
if pedido.estado != "preparacion" or not pedido.insumos_descontados:
    raise SystemExit("El pedido no quedó en preparación con los insumos descontados.")
if harina.stock_actual >= antes:
    raise SystemExit("El stock de harina no disminuyó después del descuento del BOM.")

# Transición inválida: debe responder 400
invalida = cliente.post(
    f"/api/pedidos/{pedido.pk}/cambiar_estado/",
    data={"estado": "entregado"},
    content_type="application/json",
)
print(f"Transición inválida -> HTTP {invalida.status_code} ({invalida.json()})")
if invalida.status_code != 400:
    raise SystemExit(
        f"La transición inválida respondió {invalida.status_code}, se esperaba 400."
    )
