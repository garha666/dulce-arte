"""Pruebas automáticas del núcleo de Dulce Arte.

Se ejecutan con:  python manage.py test api
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (
    Cliente,
    Despacho,
    Insumo,
    MovimientoInsumo,
    Pedido,
    PedidoDetalle,
    Perfil,
    Producto,
    RecetaInsumo,
)


class BaseDulceArteTest(TestCase):
    """Crea un escenario mínimo: usuario, insumo, producto con receta y cliente."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_test", password="Clave2026!", is_staff=True
        )
        Perfil.objects.create(user=self.admin, rol="admin")

        self.ventas = User.objects.create_user(
            username="ventas_test", password="Clave2026!"
        )
        Perfil.objects.create(user=self.ventas, rol="ventas")

        self.harina = Insumo.objects.create(
            nombre="Harina test",
            unidad="g",
            stock_actual=Decimal("1000"),
            stock_minimo=Decimal("100"),
            costo_unitario=Decimal("2"),
        )
        self.producto = Producto.objects.create(
            nombre="Torta test", precio_base=Decimal("10000"), porciones=8
        )
        RecetaInsumo.objects.create(
            producto=self.producto, insumo=self.harina, cantidad=Decimal("250")
        )
        self.cliente = Cliente.objects.create(
            nombre="Cliente test", telefono="+56900000000"
        )

    def crear_pedido(self, cantidad=1):
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            fecha_entrega=timezone.now() + timedelta(days=2),
            creado_por=self.admin,
            estado="recibido",
        )
        PedidoDetalle.objects.create(
            pedido=pedido, producto=self.producto, cantidad=cantidad
        )
        return pedido


class KanbanTest(BaseDulceArteTest):
    def test_transicion_valida_descuenta_bom_una_sola_vez(self):
        pedido = self.crear_pedido()

        pedido.cambiar_estado("preparacion", usuario=self.admin)

        self.harina.refresh_from_db()
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "preparacion")
        self.assertTrue(pedido.insumos_descontados)
        self.assertEqual(self.harina.stock_actual, Decimal("750"))
        self.assertEqual(
            MovimientoInsumo.objects.filter(tipo="consumo", pedido=pedido).count(), 1
        )

        # Volver a preparación no debe descontar de nuevo.
        pedido.cambiar_estado("horneado", usuario=self.admin)
        pedido.cambiar_estado("calidad", usuario=self.admin)
        pedido.cambiar_estado("preparacion", usuario=self.admin)
        self.harina.refresh_from_db()
        self.assertEqual(self.harina.stock_actual, Decimal("750"))

    def test_transicion_invalida_no_cambia_estado(self):
        pedido = self.crear_pedido()

        with self.assertRaises(ValidationError):
            pedido.cambiar_estado("entregado", usuario=self.admin)

        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "recibido")
        self.assertFalse(pedido.insumos_descontados)

    def test_stock_insuficiente_cancela_el_cambio(self):
        self.harina.stock_actual = Decimal("100")
        self.harina.save(update_fields=["stock_actual"])
        pedido = self.crear_pedido(cantidad=2)

        with self.assertRaises(ValidationError):
            pedido.cambiar_estado("preparacion", usuario=self.admin)

        pedido.refresh_from_db()
        self.harina.refresh_from_db()
        self.assertEqual(pedido.estado, "recibido")
        self.assertEqual(self.harina.stock_actual, Decimal("100"))


class DespachoTest(BaseDulceArteTest):
    def test_no_confirma_sin_evidencia(self):
        pedido = self.crear_pedido()
        despacho = Despacho(
            pedido=pedido,
            direccion="Calle 123",
            fecha_entrega=timezone.now(),
        )

        with self.assertRaises(ValidationError):
            despacho.full_clean()


class ApiPermisosTest(BaseDulceArteTest):
    def test_ventas_no_puede_mover_kanban(self):
        pedido = self.crear_pedido()
        cliente = APIClient()
        cliente.login(username="ventas_test", password="Clave2026!")

        respuesta = cliente.post(
            f"/api/pedidos/{pedido.pk}/cambiar_estado/",
            {"estado": "preparacion"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 403)

    def test_admin_puede_mover_kanban(self):
        pedido = self.crear_pedido()
        cliente = APIClient()
        cliente.login(username="admin_test", password="Clave2026!")

        respuesta = cliente.post(
            f"/api/pedidos/{pedido.pk}/cambiar_estado/",
            {"estado": "preparacion"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["estado"], "preparacion")

    def test_crear_pedido_por_api_asigna_codigo(self):
        cliente = APIClient()
        cliente.login(username="admin_test", password="Clave2026!")

        respuesta = cliente.post(
            "/api/pedidos/",
            {
                "cliente": self.cliente.pk,
                "fecha_entrega": (timezone.now() + timedelta(days=1)).isoformat(),
                "detalles": [{"producto": self.producto.pk, "cantidad": 1}],
            },
            format="json",
        )

        self.assertEqual(respuesta.status_code, 201)
        self.assertTrue(respuesta.json()["codigo"].startswith("PED-"))
        self.assertEqual(Decimal(respuesta.json()["total"]), Decimal("10000"))
