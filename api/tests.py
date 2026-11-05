"""Pruebas automáticas del núcleo de Dulce Arte.

Se ejecutan con:  python manage.py test api
"""

from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from PIL import Image
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

        self.cocina = User.objects.create_user(
            username="cocina_test", password="Clave2026!"
        )
        Perfil.objects.create(user=self.cocina, rol="cocina")

        self.despacho_user = User.objects.create_user(
            username="despacho_test", password="Clave2026!"
        )
        Perfil.objects.create(user=self.despacho_user, rol="despacho")

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

    def crear_pedido(self, cantidad=1, estado="recibido"):
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            fecha_entrega=timezone.now() + timedelta(days=2),
            creado_por=self.admin,
            estado=estado,
        )
        PedidoDetalle.objects.create(
            pedido=pedido, producto=self.producto, cantidad=cantidad
        )
        return pedido

    def crear_despacho(self, pedido, confirmado=False):
        despacho = Despacho.objects.create(
            pedido=pedido, direccion="Calle 123, Temuco"
        )
        if confirmado:
            despacho.fecha_entrega = timezone.now()
            despacho.receptor_nombre = "Receptora"
            despacho.comprobante = "comprobantes/test.png"
            despacho.save(
                update_fields=["fecha_entrega", "receptor_nombre", "comprobante"]
            )
        return despacho


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

    def test_no_permite_crear_pedido_sin_detalles(self):
        cliente = APIClient()
        cliente.login(username="admin_test", password="Clave2026!")

        respuesta = cliente.post(
            "/api/pedidos/",
            {
                "cliente": self.cliente.pk,
                "fecha_entrega": (timezone.now() + timedelta(days=1)).isoformat(),
                "detalles": [],
            },
            format="json",
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_estado_no_se_puede_cambiar_por_patch(self):
        pedido = self.crear_pedido()
        cliente = APIClient()
        cliente.login(username="admin_test", password="Clave2026!")

        respuesta = cliente.patch(
            f"/api/pedidos/{pedido.pk}/",
            {"estado": "entregado"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 200)  # el campo se ignora
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "recibido")


class PermisosRolApiTest(BaseDulceArteTest):
    """La API debe respetar los mismos roles que las páginas HTML."""

    def _cliente(self, username):
        cliente = APIClient()
        cliente.login(username=username, password="Clave2026!")
        return cliente

    def test_ventas_no_puede_descontar_insumos(self):
        pedido = self.crear_pedido()
        cliente = self._cliente("ventas_test")

        respuesta = cliente.post(
            f"/api/pedidos/{pedido.pk}/descontar_insumos/",
            {},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 403)
        pedido.refresh_from_db()
        self.harina.refresh_from_db()
        self.assertFalse(pedido.insumos_descontados)
        self.assertEqual(self.harina.stock_actual, Decimal("1000"))

    def test_cocina_no_puede_crear_pedido(self):
        cliente = self._cliente("cocina_test")

        respuesta = cliente.post("/api/pedidos/", {}, format="json")

        self.assertEqual(respuesta.status_code, 403)

    def test_cocina_no_puede_editar_ni_borrar_pedido(self):
        pedido = self.crear_pedido()
        cliente = self._cliente("cocina_test")

        editar = cliente.patch(
            f"/api/pedidos/{pedido.pk}/",
            {"descripcion_diseno": "Cambio no autorizado"},
            format="json",
        )
        borrar = cliente.delete(f"/api/pedidos/{pedido.pk}/")

        self.assertEqual(editar.status_code, 403)
        self.assertEqual(borrar.status_code, 403)
        pedido.refresh_from_db()
        self.assertNotEqual(pedido.descripcion_diseno, "Cambio no autorizado")

    def test_cocina_no_puede_crear_ni_gestionar_despacho(self):
        pedido = self.crear_pedido(estado="listo")
        despacho = self.crear_despacho(pedido)
        cliente = self._cliente("cocina_test")

        crear = cliente.post("/api/despachos/", {}, format="json")
        editar = cliente.patch(
            f"/api/despachos/{despacho.pk}/",
            {"direccion": "Otra dirección"},
            format="json",
        )
        borrar = cliente.delete(f"/api/despachos/{despacho.pk}/")

        self.assertEqual(crear.status_code, 403)
        self.assertEqual(editar.status_code, 403)
        self.assertEqual(borrar.status_code, 403)

    def test_despacho_puede_crear_despacho(self):
        pedido = self.crear_pedido(estado="listo")
        cliente = self._cliente("despacho_test")

        respuesta = cliente.post(
            "/api/despachos/",
            {"pedido": pedido.pk, "direccion": "Calle 456, Temuco"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 201)
        self.assertTrue(Despacho.objects.filter(pedido=pedido).exists())


class DespachoFlujoTest(BaseDulceArteTest):
    def test_no_crea_despacho_si_pedido_no_esta_listo(self):
        pedido = self.crear_pedido(estado="recibido")
        self.client.login(username="admin_test", password="Clave2026!")

        respuesta = self.client.post(
            "/despachos/crear/",
            {"pedido": pedido.pk, "direccion": "Calle 123"},
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(Despacho.objects.filter(pedido=pedido).exists())

        cliente = APIClient()
        cliente.login(username="admin_test", password="Clave2026!")
        respuesta_api = cliente.post(
            "/api/despachos/",
            {"pedido": pedido.pk, "direccion": "Calle 123"},
            format="json",
        )
        self.assertEqual(respuesta_api.status_code, 400)
        self.assertFalse(Despacho.objects.filter(pedido=pedido).exists())

    def test_no_permite_entregar_sin_despacho_confirmado(self):
        pedido = self.crear_pedido(estado="listo")

        with self.assertRaises(ValidationError):
            pedido.cambiar_estado("entregado", usuario=self.admin)

        self.crear_despacho(pedido)
        with self.assertRaises(ValidationError):
            pedido.cambiar_estado("entregado", usuario=self.admin)

        cliente = APIClient()
        cliente.login(username="admin_test", password="Clave2026!")
        respuesta = cliente.post(
            f"/api/pedidos/{pedido.pk}/cambiar_estado/",
            {"estado": "entregado"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 400)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "listo")

    def test_permite_entregar_con_despacho_confirmado(self):
        pedido = self.crear_pedido(estado="listo")
        self.crear_despacho(pedido, confirmado=True)

        pedido.cambiar_estado("entregado", usuario=self.admin)

        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "entregado")

    def test_confirmar_despacho_exige_receptor(self):
        pedido = self.crear_pedido(estado="listo")
        despacho = self.crear_despacho(pedido)
        self.client.login(username="admin_test", password="Clave2026!")

        respuesta = self.client.post(
            f"/despachos/{despacho.pk}/confirmar/",
            {"receptor_nombre": ""},
        )

        self.assertEqual(respuesta.status_code, 302)
        despacho.refresh_from_db()
        self.assertFalse(despacho.confirmado)

    def test_confirmar_despacho_no_sobrescribe_confirmado(self):
        pedido = self.crear_pedido(estado="listo")
        despacho = self.crear_despacho(pedido, confirmado=True)
        self.client.login(username="admin_test", password="Clave2026!")

        respuesta = self.client.post(
            f"/despachos/{despacho.pk}/confirmar/",
            {"receptor_nombre": "Otra persona"},
        )

        self.assertEqual(respuesta.status_code, 302)
        despacho.refresh_from_db()
        self.assertEqual(despacho.receptor_nombre, "Receptora")

    def test_confirmar_despacho_marca_pedido_entregado(self):
        pedido = self.crear_pedido(estado="listo")
        despacho = self.crear_despacho(pedido)

        buffer = BytesIO()
        Image.new("RGB", (1, 1), "white").save(buffer, format="PNG")
        archivo = SimpleUploadedFile(
            "comprobante.png", buffer.getvalue(), content_type="image/png"
        )

        with TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=media):
                self.client.login(username="admin_test", password="Clave2026!")
                respuesta = self.client.post(
                    f"/despachos/{despacho.pk}/confirmar/",
                    {
                        "receptor_nombre": "Ana Pérez",
                        "comprobante": archivo,
                    },
                )

        self.assertEqual(respuesta.status_code, 302)
        despacho.refresh_from_db()
        pedido.refresh_from_db()
        self.assertTrue(despacho.confirmado)
        self.assertEqual(pedido.estado, "entregado")


class BomProteccionTest(BaseDulceArteTest):
    def test_no_edita_pedido_con_insumos_descontados(self):
        pedido = self.crear_pedido()
        pedido.cambiar_estado("preparacion", usuario=self.admin)
        cliente = APIClient()
        cliente.login(username="admin_test", password="Clave2026!")

        respuesta = cliente.patch(
            f"/api/pedidos/{pedido.pk}/",
            {"descripcion_diseno": "Cambio posterior al BOM"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 400)
        pedido.refresh_from_db()
        self.assertNotEqual(
            pedido.descripcion_diseno, "Cambio posterior al BOM"
        )

    def test_no_elimina_pedido_con_insumos_descontados(self):
        pedido = self.crear_pedido()
        pedido.cambiar_estado("preparacion", usuario=self.admin)
        cliente = APIClient()
        cliente.login(username="admin_test", password="Clave2026!")

        respuesta = cliente.delete(f"/api/pedidos/{pedido.pk}/")

        self.assertEqual(respuesta.status_code, 400)
        self.assertTrue(Pedido.objects.filter(pk=pedido.pk).exists())

    def test_permite_editar_antes_del_bom(self):
        pedido = self.crear_pedido()
        cliente = APIClient()
        cliente.login(username="admin_test", password="Clave2026!")

        respuesta = cliente.patch(
            f"/api/pedidos/{pedido.pk}/",
            {"descripcion_diseno": "Ajuste de cotización"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 200)


class FrontendSeguridadTest(SimpleTestCase):
    def test_pedidos_js_escapa_cliente_nombre(self):
        ruta = Path(settings.BASE_DIR) / "static" / "js" / "pedidos.js"
        contenido = ruta.read_text(encoding="utf-8")

        self.assertIn("function escapeHtml", contenido)
        self.assertIn("escapeHtml(p.cliente_nombre)", contenido)
        self.assertNotIn("<td>${p.cliente_nombre}</td>", contenido)
