"""Pruebas automáticas de Dulce Arte.

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
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from .models import (
    CategoriaProducto,
    Cliente,
    Despacho,
    Insumo,
    MovimientoInsumo,
    Pago,
    Pedido,
    PedidoDetalle,
    Perfil,
    Producto,
    RecetaInsumo,
)

CLAVE = "Clave2026!"


def fecha_valida(dias=5):
    """Fecha futura en horario de atención (12:00, hora de Santiago)."""
    base = timezone.localtime() + timedelta(days=dias)
    return base.replace(hour=12, minute=0, second=0, microsecond=0)


class BaseDulceArteTest(TestCase):
    """Escenario mínimo: roles, insumo, producto con receta y cliente con cuenta."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_test", password=CLAVE, is_staff=True, is_superuser=True
        )
        Perfil.objects.create(user=self.admin, rol="admin")

        self.ventas = User.objects.create_user(username="ventas_test", password=CLAVE)
        Perfil.objects.create(user=self.ventas, rol="ventas")

        self.cocina = User.objects.create_user(username="cocina_test", password=CLAVE)
        Perfil.objects.create(user=self.cocina, rol="cocina")

        self.despacho_user = User.objects.create_user(
            username="despacho_test", password=CLAVE
        )
        Perfil.objects.create(user=self.despacho_user, rol="despacho")

        self.cliente_user = User.objects.create_user(
            username="cliente_test", password=CLAVE, email="cliente@test.cl"
        )
        Perfil.objects.create(user=self.cliente_user, rol="cliente")

        self.harina = Insumo.objects.create(
            nombre="Harina test",
            unidad="g",
            stock_actual=Decimal("1000"),
            stock_minimo=Decimal("100"),
            costo_unitario=Decimal("2"),
        )
        self.categoria = CategoriaProducto.objects.create(nombre="Tortas test")
        self.producto = Producto.objects.create(
            nombre="Torta test",
            precio_base=Decimal("10000"),
            porciones=8,
            categoria=self.categoria,
        )
        RecetaInsumo.objects.create(
            producto=self.producto, insumo=self.harina, cantidad=Decimal("250")
        )
        self.cliente = Cliente.objects.create(
            user=self.cliente_user,
            nombre="Cliente test",
            telefono="+56900000000",
            email="cliente@test.cl",
        )

    def crear_pedido(
        self,
        cantidad=1,
        estado="recibido",
        modalidad="retiro",
        cliente=None,
    ):
        pedido = Pedido.objects.create(
            cliente=cliente or self.cliente,
            modalidad=modalidad,
            fecha_entrega=fecha_valida(),
            creado_por=self.admin,
            estado=estado,
            direccion_entrega="Calle 123, Temuco" if modalidad == "despacho" else "",
        )
        PedidoDetalle.objects.create(
            pedido=pedido, producto=self.producto, cantidad=cantidad
        )
        return pedido

    def pagar(self, pedido, monto="20000"):
        return Pago.objects.create(
            pedido=pedido, monto=Decimal(monto), metodo="transferencia"
        )

    def confirmar(self, pedido):
        self.pagar(pedido)
        return pedido.cambiar_estado("confirmado", usuario=self.ventas)


class FlujoPedidoTest(BaseDulceArteTest):
    def test_no_se_prepara_sin_confirmar(self):
        pedido = self.crear_pedido()
        with self.assertRaises(ValidationError):
            pedido.cambiar_estado("preparacion", usuario=self.cocina)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "recibido")

    def test_no_se_confirma_sin_pago(self):
        pedido = self.crear_pedido()
        with self.assertRaises(ValidationError):
            pedido.cambiar_estado("confirmado", usuario=self.ventas)

    def test_confirmar_marca_responsable(self):
        pedido = self.crear_pedido()
        self.confirmar(pedido)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "confirmado")
        self.assertEqual(pedido.confirmado_por, self.ventas)
        self.assertIsNotNone(pedido.confirmado_en)

    def test_descuenta_bom_una_sola_vez(self):
        pedido = self.crear_pedido()
        self.confirmar(pedido)

        pedido.cambiar_estado("preparacion", usuario=self.cocina)

        self.harina.refresh_from_db()
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "preparacion")
        self.assertTrue(pedido.insumos_descontados)
        self.assertEqual(self.harina.stock_actual, Decimal("750"))
        self.assertEqual(
            MovimientoInsumo.objects.filter(tipo="consumo", pedido=pedido).count(), 1
        )

        pedido.cambiar_estado("horneado", usuario=self.cocina)
        pedido.cambiar_estado("calidad", usuario=self.admin)
        pedido.cambiar_estado("preparacion", usuario=self.cocina)
        self.harina.refresh_from_db()
        self.assertEqual(self.harina.stock_actual, Decimal("750"))

    def test_cancelar_repone_insumos(self):
        pedido = self.crear_pedido()
        self.confirmar(pedido)
        pedido.cambiar_estado("preparacion", usuario=self.cocina)

        pedido.cambiar_estado("cancelado", usuario=self.admin)

        self.harina.refresh_from_db()
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "cancelado")
        self.assertFalse(pedido.insumos_descontados)
        self.assertEqual(self.harina.stock_actual, Decimal("1000"))
        self.assertEqual(
            MovimientoInsumo.objects.filter(tipo="entrada", pedido=pedido).count(), 1
        )

    def test_stock_insuficiente_cancela_el_cambio(self):
        self.harina.stock_actual = Decimal("100")
        self.harina.save(update_fields=["stock_actual"])
        pedido = self.crear_pedido(cantidad=2)
        self.confirmar(pedido)

        with self.assertRaises(ValidationError):
            pedido.cambiar_estado("preparacion", usuario=self.cocina)

        pedido.refresh_from_db()
        self.harina.refresh_from_db()
        self.assertEqual(pedido.estado, "confirmado")
        self.assertEqual(self.harina.stock_actual, Decimal("100"))

    def test_transicion_invalida_no_cambia_estado(self):
        pedido = self.crear_pedido()
        with self.assertRaises(ValidationError):
            pedido.cambiar_estado("entregado", usuario=self.admin)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "recibido")


class PagoTest(BaseDulceArteTest):
    def test_estado_pago_se_calcula_desde_los_pagos(self):
        pedido = self.crear_pedido()
        self.assertEqual(pedido.estado_pago, "pendiente")
        self.assertEqual(pedido.saldo, Decimal("10000"))

        self.pagar(pedido, "4000")
        self.assertEqual(pedido.total_pagado, Decimal("4000"))
        self.assertEqual(pedido.estado_pago, "parcial")

        self.pagar(pedido, "6000")
        self.assertEqual(pedido.estado_pago, "pagado")
        self.assertEqual(pedido.saldo, Decimal("0"))

    def test_monto_debe_ser_positivo(self):
        pedido = self.crear_pedido()
        pago = Pago(pedido=pedido, monto=Decimal("0"), metodo="efectivo")
        with self.assertRaises(ValidationError):
            pago.full_clean()


class AgendaTest(BaseDulceArteTest):
    def test_pedido_web_exige_anticipacion(self):
        pedido = Pedido(
            cliente=self.cliente,
            canal="web",
            modalidad="retiro",
            fecha_entrega=timezone.localtime() + timedelta(hours=10),
        )
        with self.assertRaises(ValidationError):
            pedido.full_clean()

    def test_pedido_web_respeta_cupo_diario(self):
        fecha = fecha_valida()
        for _ in range(Pedido.CUPO_DIARIO):
            Pedido.objects.create(
                cliente=self.cliente, fecha_entrega=fecha, modalidad="retiro"
            )
        with self.assertRaises(ValidationError):
            Pedido.validar_agenda(fecha, exigir_anticipacion=False)

    def test_horario_de_atencion(self):
        fecha = fecha_valida().replace(hour=23)
        with self.assertRaises(ValidationError):
            Pedido.validar_agenda(fecha, exigir_anticipacion=False)

    def test_despacho_exige_direccion(self):
        pedido = Pedido(
            cliente=self.cliente,
            modalidad="despacho",
            fecha_entrega=fecha_valida(),
        )
        with self.assertRaises(ValidationError):
            pedido.full_clean()


class DespachoFlujoTest(BaseDulceArteTest):
    def _despacho_listo(self, confirmado=False):
        pedido = self.crear_pedido(estado="listo", modalidad="despacho")
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
        return pedido, despacho

    def test_despacho_crear_marca_pedido_despachado(self):
        pedido = self.crear_pedido(estado="listo", modalidad="despacho")
        self.client.login(username="despacho_test", password=CLAVE)

        respuesta = self.client.post(
            reverse("despacho_crear"),
            {
                "pedido": pedido.pk,
                "repartidor": self.despacho_user.pk,
                "direccion": "Calle 456, Temuco",
                "observaciones": "",
            },
        )

        self.assertEqual(respuesta.status_code, 302)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "despachado")
        despacho = Despacho.objects.get(pedido=pedido)
        self.assertIsNotNone(despacho.fecha_salida)

    def test_no_crea_despacho_si_pedido_no_esta_listo(self):
        pedido = self.crear_pedido(estado="confirmado", modalidad="despacho")
        self.client.login(username="despacho_test", password=CLAVE)

        self.client.post(
            reverse("despacho_crear"),
            {"pedido": pedido.pk, "direccion": "Calle 123"},
        )

        self.assertFalse(Despacho.objects.filter(pedido=pedido).exists())

    def test_no_entregar_sin_despacho_confirmado(self):
        pedido, despacho = self._despacho_listo()
        pedido.cambiar_estado("despachado", usuario=self.despacho_user)

        with self.assertRaises(ValidationError):
            pedido.cambiar_estado("entregado", usuario=self.despacho_user)

    def test_no_confirma_sin_evidencia(self):
        pedido = self.crear_pedido(estado="listo", modalidad="despacho")
        despacho = Despacho(pedido=pedido, direccion="Calle 123")
        despacho.fecha_entrega = timezone.now()
        despacho.receptor_nombre = "Ana"
        with self.assertRaises(ValidationError):
            despacho.full_clean()

    def test_confirmar_entrega_marca_pedido_entregado(self):
        pedido, despacho = self._despacho_listo()
        pedido.cambiar_estado("despachado", usuario=self.despacho_user)

        buffer = BytesIO()
        Image.new("RGB", (1, 1), "white").save(buffer, format="PNG")
        archivo = SimpleUploadedFile(
            "comprobante.png", buffer.getvalue(), content_type="image/png"
        )

        with TemporaryDirectory() as media:
            with override_settings(MEDIA_ROOT=media):
                self.client.login(username="despacho_test", password=CLAVE)
                respuesta = self.client.post(
                    reverse("despacho_confirmar", args=[despacho.pk]),
                    {"receptor_nombre": "Ana Pérez", "comprobante": archivo},
                )

        self.assertEqual(respuesta.status_code, 302)
        despacho.refresh_from_db()
        pedido.refresh_from_db()
        self.assertTrue(despacho.confirmado)
        self.assertEqual(despacho.confirmado_por, self.despacho_user)
        self.assertEqual(pedido.estado, "entregado")

    def test_retiro_exige_quien_retira(self):
        pedido = self.crear_pedido(estado="listo", modalidad="retiro")
        with self.assertRaises(ValidationError):
            pedido.cambiar_estado("entregado", usuario=self.admin)

        pedido.retirado_por = "María"
        pedido.save(update_fields=["retirado_por"])
        pedido.cambiar_estado("entregado", usuario=self.admin)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "entregado")


class TiendaTest(BaseDulceArteTest):
    def test_catalogo_publico(self):
        respuesta = self.client.get(reverse("tienda"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Torta test")

    def test_agregar_al_carrito_y_ver_carrito(self):
        respuesta = self.client.post(
            reverse("carrito_agregar", args=[self.producto.pk]),
            {"cantidad": 2, "personalizacion": "Sin azúcar"},
        )
        self.assertEqual(respuesta.status_code, 302)

        carrito = self.client.get(reverse("carrito"))
        self.assertContains(carrito, "Torta test")
        self.assertContains(carrito, "Sin azúcar")

    def test_checkout_crea_pedido_web(self):
        self.client.post(
            reverse("carrito_agregar", args=[self.producto.pk]), {"cantidad": 1}
        )

        respuesta = self.client.post(
            reverse("checkout"),
            {
                "nombre": "Cliente test",
                "telefono": "+56900000000",
                "email": "cliente@test.cl",
                "modalidad": "retiro",
                "direccion_entrega": "",
                "fecha_entrega": fecha_valida().strftime("%Y-%m-%dT%H:%M"),
                "descripcion_diseno": "Con dedicatoria",
                "metodo_pago": "transferencia",
                "acepta_terminos": "on",
            },
        )

        self.assertEqual(respuesta.status_code, 302)
        pedido = Pedido.objects.get(canal="web")
        self.assertEqual(pedido.estado, "recibido")
        self.assertEqual(pedido.cliente, self.cliente)
        self.assertEqual(pedido.estado_pago, "pendiente")
        self.assertRedirects(
            respuesta, reverse("seguimiento_detalle", args=[pedido.token_seguimiento])
        )

    def test_checkout_rechaza_fecha_sin_anticipacion(self):
        self.client.post(
            reverse("carrito_agregar", args=[self.producto.pk]), {"cantidad": 1}
        )
        temprano = timezone.localtime() + timedelta(hours=12)

        respuesta = self.client.post(
            reverse("checkout"),
            {
                "nombre": "Cliente test",
                "telefono": "+56900000000",
                "email": "cliente@test.cl",
                "modalidad": "retiro",
                "fecha_entrega": temprano.strftime("%Y-%m-%dT%H:%M"),
                "metodo_pago": "efectivo",
                "acepta_terminos": "on",
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Pedido.objects.filter(canal="web").exists())

    def test_seguimiento_por_token(self):
        pedido = self.crear_pedido()
        respuesta = self.client.get(
            reverse("seguimiento_detalle", args=[pedido.token_seguimiento])
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, pedido.codigo)
        self.assertNotContains(respuesta, "+56900000000")

    def test_registro_crea_cuenta_cliente(self):
        respuesta = self.client.post(
            reverse("registro"),
            {
                "nombre": "Nueva",
                "apellido": "Clienta",
                "username": "nueva_clienta",
                "email": "nueva@test.cl",
                "telefono": "+56911111111",
                "password1": "Secreta2026!",
                "password2": "Secreta2026!",
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        user = User.objects.get(username="nueva_clienta")
        self.assertEqual(user.perfil.rol, "cliente")
        self.assertEqual(user.cliente.telefono, "+56911111111")

    def test_mis_pedidos_solo_muestra_los_propios(self):
        propio = self.crear_pedido()
        otro_cliente = Cliente.objects.create(nombre="Otra", telefono="+56922222222")
        ajeno = self.crear_pedido(cliente=otro_cliente)

        self.client.login(username="cliente_test", password=CLAVE)
        respuesta = self.client.get(reverse("mis_pedidos"))

        self.assertContains(respuesta, propio.codigo)
        self.assertNotContains(respuesta, ajeno.codigo)

    def test_no_puede_ver_pedido_ajeno(self):
        otro_cliente = Cliente.objects.create(nombre="Otra", telefono="+56922222222")
        ajeno = self.crear_pedido(cliente=otro_cliente)

        self.client.login(username="cliente_test", password=CLAVE)
        respuesta = self.client.get(reverse("pedido_detalle", args=[ajeno.pk]))

        self.assertEqual(respuesta.status_code, 302)


class ApiSoloAdminTest(BaseDulceArteTest):
    def _api(self, username):
        cliente = APIClient()
        cliente.login(username=username, password=CLAVE)
        return cliente

    def test_anonimo_no_accede_a_la_api(self):
        respuesta = APIClient().get("/api/pedidos/")
        self.assertIn(respuesta.status_code, (401, 403))

    def test_roles_operativos_no_leen_la_api(self):
        for username in ("ventas_test", "cocina_test", "despacho_test"):
            respuesta = self._api(username).get("/api/pedidos/")
            self.assertEqual(respuesta.status_code, 403, username)

    def test_cliente_no_accede_a_la_api(self):
        respuesta = self._api("cliente_test").get("/api/productos/")
        self.assertEqual(respuesta.status_code, 403)

    def test_admin_administra_la_api(self):
        respuesta = self._api("admin_test").get("/api/productos/")
        self.assertEqual(respuesta.status_code, 200)

    def test_admin_mueve_kanban_por_api(self):
        pedido = self.crear_pedido()
        self.pagar(pedido)
        pedido.cambiar_estado("confirmado", usuario=self.ventas)

        respuesta = self._api("admin_test").post(
            f"/api/pedidos/{pedido.pk}/cambiar_estado/",
            {"estado": "preparacion"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["estado"], "preparacion")

    def test_no_permite_crear_pedido_sin_detalles(self):
        respuesta = self._api("admin_test").post(
            "/api/pedidos/",
            {
                "cliente": self.cliente.pk,
                "fecha_entrega": fecha_valida().isoformat(),
                "detalles": [],
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, 400)

    def test_estado_no_se_puede_cambiar_por_patch(self):
        pedido = self.crear_pedido()
        respuesta = self._api("admin_test").patch(
            f"/api/pedidos/{pedido.pk}/", {"estado": "entregado"}, format="json"
        )
        self.assertEqual(respuesta.status_code, 200)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "recibido")


class BomProteccionTest(BaseDulceArteTest):
    def test_no_edita_pedido_con_insumos_descontados(self):
        pedido = self.crear_pedido()
        self.confirmar(pedido)
        pedido.cambiar_estado("preparacion", usuario=self.cocina)

        cliente = APIClient()
        cliente.login(username="admin_test", password=CLAVE)
        respuesta = cliente.patch(
            f"/api/pedidos/{pedido.pk}/",
            {"descripcion_diseno": "Cambio posterior"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 400)

    def test_no_elimina_pedido_con_insumos_descontados(self):
        pedido = self.crear_pedido()
        self.confirmar(pedido)
        pedido.cambiar_estado("preparacion", usuario=self.cocina)

        cliente = APIClient()
        cliente.login(username="admin_test", password=CLAVE)
        respuesta = cliente.delete(f"/api/pedidos/{pedido.pk}/")

        self.assertEqual(respuesta.status_code, 400)
        self.assertTrue(Pedido.objects.filter(pk=pedido.pk).exists())

    def test_permite_editar_antes_del_bom(self):
        pedido = self.crear_pedido()
        cliente = APIClient()
        cliente.login(username="admin_test", password=CLAVE)

        respuesta = cliente.patch(
            f"/api/pedidos/{pedido.pk}/",
            {"descripcion_diseno": "Ajuste de cotización"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 200)


class PaginasInternasTest(BaseDulceArteTest):
    def test_cocina_entra_al_kanban(self):
        self.client.login(username="cocina_test", password=CLAVE)
        respuesta = self.client.get(reverse("kanban"))
        self.assertEqual(respuesta.status_code, 200)

    def test_cliente_no_entra_al_kanban(self):
        self.client.login(username="cliente_test", password=CLAVE)
        respuesta = self.client.get(reverse("kanban"))
        self.assertEqual(respuesta.status_code, 302)

    def test_ventas_registra_pedido_por_formulario(self):
        self.client.login(username="ventas_test", password=CLAVE)
        respuesta = self.client.post(
            reverse("pedido_crear"),
            {
                "cliente": self.cliente.pk,
                "canal": "mostrador",
                "modalidad": "retiro",
                "fecha_entrega": fecha_valida().strftime("%Y-%m-%dT%H:%M"),
                "direccion_entrega": "",
                "telefono_contacto": "+56900000000",
                "descripcion_diseno": "Pedido de mostrador",
                "costo_despacho": "0",
                "observaciones": "",
                "producto": self.producto.pk,
                "cantidad": 1,
                "personalizacion": "",
            },
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Pedido.objects.filter(descripcion_diseno="Pedido de mostrador").exists())

    def test_ventas_registra_pago(self):
        pedido = self.crear_pedido()
        self.client.login(username="ventas_test", password=CLAVE)

        respuesta = self.client.post(
            reverse("pedido_registrar_pago", args=[pedido.pk]),
            {
                "monto": "5000",
                "metodo": "efectivo",
                "tipo": "anticipo",
                "referencia": "Caja 1",
            },
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(pedido.total_pagado, Decimal("5000"))

    def test_detalle_muestra_editar_solo_a_admin_y_ventas(self):
        pedido = self.crear_pedido()

        for usuario, esperado in (
            ("admin_test", True),
            ("ventas_test", True),
            ("cocina_test", False),
        ):
            self.client.login(username=usuario, password=CLAVE)
            respuesta = self.client.get(
                reverse("pedido_detalle", args=[pedido.pk])
            )
            self.assertEqual(respuesta.status_code, 200, usuario)
            self.assertIs(respuesta.context["puede_editar"], esperado, usuario)


class FrontendSeguridadTest(SimpleTestCase):
    def test_panel_interno_no_usa_la_api(self):
        base = Path(settings.BASE_DIR) / "templates"
        for nombre in ("pedidos.html", "kanban.html", "despachos.html", "pedido_detalle.html"):
            contenido = (base / nombre).read_text(encoding="utf-8")
            self.assertNotIn("/api/", contenido, nombre)
            self.assertNotIn("fetch(", contenido, nombre)

    def test_scripts_obsoletos_eliminados(self):
        js = Path(settings.BASE_DIR) / "static" / "js"
        self.assertFalse((js / "pedidos.js").exists())
        self.assertFalse((js / "kanban.js").exists())


class PermisosPorRolTest(BaseDulceArteTest):
    def test_ventas_no_inicia_preparacion(self):
        pedido = self.crear_pedido()
        self.confirmar(pedido)

        with self.assertRaises(ValidationError):
            pedido.cambiar_estado("preparacion", usuario=self.ventas)

        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "confirmado")

    def test_cocina_no_confirma_pedidos(self):
        pedido = self.crear_pedido()
        self.pagar(pedido)

        with self.assertRaises(ValidationError):
            pedido.cambiar_estado("confirmado", usuario=self.cocina)

        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "recibido")

    def test_transiciones_visibles_por_rol(self):
        pedido = self.crear_pedido()
        self.assertEqual(
            [clave for clave, _ in pedido.transiciones_para("ventas")],
            ["confirmado", "cancelado"],
        )
        self.assertEqual(pedido.transiciones_para("cocina"), [])

        self.confirmar(pedido)
        self.assertEqual(
            [clave for clave, _ in pedido.transiciones_para("cocina")],
            ["preparacion"],
        )


class EquipoTest(BaseDulceArteTest):
    def test_solo_admin_entra_a_equipo(self):
        self.client.login(username="ventas_test", password=CLAVE)
        self.assertEqual(self.client.get(reverse("equipo")).status_code, 302)

        self.client.login(username="admin_test", password=CLAVE)
        self.assertEqual(self.client.get(reverse("equipo")).status_code, 200)

    def test_admin_crea_usuario_interno_con_atributos(self):
        self.client.login(username="admin_test", password=CLAVE)
        respuesta = self.client.post(
            reverse("equipo_crear_usuario"),
            {
                "nombre": "Nueva",
                "apellido": "Repostera",
                "username": "repostera",
                "email": "repostera@test.cl",
                "telefono": "+56955555555",
                "rol": "cocina",
                "turno": "manana",
                "especialidad": "Decoración",
                "zona": "",
                "vehiculo": "",
                "notas": "Refuerzo de fin de semana",
                "password1": "Secreta2026!",
                "password2": "Secreta2026!",
            },
        )

        self.assertEqual(respuesta.status_code, 302)
        user = User.objects.get(username="repostera")
        self.assertEqual(user.perfil.rol, "cocina")
        self.assertEqual(user.perfil.turno, "manana")
        self.assertEqual(user.perfil.especialidad, "Decoración")

    def test_admin_crea_cliente_con_cuenta(self):
        self.client.login(username="admin_test", password=CLAVE)
        respuesta = self.client.post(
            reverse("equipo_crear_cliente"),
            {
                "nombre": "Cliente Nuevo",
                "telefono": "+56944444444",
                "email": "nuevo@test.cl",
                "direccion": "Calle 1",
                "username": "nuevo_cliente",
                "password1": "Secreta2026!",
                "password2": "Secreta2026!",
            },
        )

        self.assertEqual(respuesta.status_code, 302)
        cliente = Cliente.objects.get(nombre="Cliente Nuevo")
        self.assertEqual(cliente.user.username, "nuevo_cliente")
        self.assertEqual(cliente.user.perfil.rol, "cliente")


class EdicionPedidoTest(BaseDulceArteTest):
    def _datos_edicion(self, pedido, detalle, **cambios):
        datos = {
            "cliente": pedido.cliente_id,
            "canal": "mostrador",
            "modalidad": "retiro",
            "fecha_entrega": fecha_valida().strftime("%Y-%m-%dT%H:%M"),
            "direccion_entrega": "",
            "telefono_contacto": "+56900000000",
            "descripcion_diseno": "Diseño actualizado",
            "costo_despacho": "0",
            "observaciones": "",
            "retirado_por": "",
            "detalles-TOTAL_FORMS": "1",
            "detalles-INITIAL_FORMS": "1",
            "detalles-MIN_NUM_FORMS": "0",
            "detalles-MAX_NUM_FORMS": "1000",
            "detalles-0-id": detalle.pk,
            "detalles-0-producto": self.producto.pk,
            "detalles-0-cantidad": "2",
            "detalles-0-precio_unitario": "10000",
            "detalles-0-personalizacion": "Sin nueces",
        }
        datos.update(cambios)
        return datos

    def test_admin_edita_pedido_antes_del_bom(self):
        pedido = self.crear_pedido()
        detalle = pedido.detalles.get()
        self.client.login(username="admin_test", password=CLAVE)

        respuesta = self.client.post(
            reverse("pedido_editar", args=[pedido.pk]),
            self._datos_edicion(pedido, detalle),
        )

        self.assertEqual(respuesta.status_code, 302)
        pedido.refresh_from_db()
        detalle.refresh_from_db()
        self.assertEqual(pedido.descripcion_diseno, "Diseño actualizado")
        self.assertEqual(detalle.cantidad, 2)

    def test_no_edita_pedido_con_insumos_descontados(self):
        pedido = self.crear_pedido()
        self.confirmar(pedido)
        pedido.cambiar_estado("preparacion", usuario=self.cocina)
        self.client.login(username="admin_test", password=CLAVE)

        respuesta = self.client.get(reverse("pedido_editar", args=[pedido.pk]))

        self.assertEqual(respuesta.status_code, 302)
        pedido.refresh_from_db()
        self.assertEqual(pedido.descripcion_diseno, "")


class ImagenYHealthTest(BaseDulceArteTest):
    def test_producto_usa_imagen_de_demostracion(self):
        self.assertEqual(
            self.producto.imagen_url, "/static/IMAGES/productos/default.jpg"
        )
        self.producto.imagen_estatica = "productos/chocolate.jpg"
        self.assertEqual(
            self.producto.imagen_url, "/static/IMAGES/productos/chocolate.jpg"
        )

    def test_health_responde_ok(self):
        respuesta = self.client.get(reverse("health"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["status"], "ok")
