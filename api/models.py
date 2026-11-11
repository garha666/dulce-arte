"""
Modelos del dominio: Dulce Arte (pastelería artesanal).

Diseño en Tercera Forma Normal (3FN):
  - 1FN: todos los campos son atómicos (sin listas ni campos compuestos).
  - 2FN: cada atributo depende de la PK de su propia tabla.
  - 3FN: los datos de una entidad no se repiten en otra tabla:
         la relación receta <-> insumo vive en la tabla intermedia RecetaInsumo
         (equivalente al ejemplo libro-autor-editorial de la unidad de BD).
"""

import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


# --------------------------------------------------------------------------- #
#  Usuarios y roles
# --------------------------------------------------------------------------- #
class Perfil(models.Model):
    """Rol del usuario dentro de la pastelería (relación 1 a 1 con User)."""

    ROLES = [
        ("admin", "Administrador"),
        ("ventas", "Ventas / Cotizaciones"),
        ("cocina", "Cocina"),
        ("calidad", "Control de calidad"),
        ("despacho", "Despacho"),
        ("cliente", "Cliente"),
    ]

    TURNOS = [
        ("manana", "Mañana (09:00–14:00)"),
        ("tarde", "Tarde (14:00–19:00)"),
        ("completo", "Jornada completa"),
        ("part-time", "Part-time / refuerzo"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="perfil"
    )
    rol = models.CharField(max_length=20, choices=ROLES, default="cliente")
    telefono = models.CharField(max_length=20, blank=True)
    turno = models.CharField(max_length=20, choices=TURNOS, blank=True)
    especialidad = models.CharField(
        max_length=80,
        blank=True,
        help_text="Ej.: repostería, decoración, control de calidad, reparto.",
    )
    zona = models.CharField(
        max_length=80,
        blank=True,
        help_text="Solo despacho: sector o comuna asignada.",
    )
    vehiculo = models.CharField(
        max_length=60,
        blank=True,
        help_text="Solo despacho: furgón, moto, bicicleta u otro.",
    )
    notas = models.CharField(
        max_length=200, blank=True, help_text="Observaciones del equipo."
    )

    class Meta:
        verbose_name = "Perfil de usuario"
        verbose_name_plural = "Perfiles de usuario"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_rol_display()})"

    @property
    def resumen(self):
        """Línea corta con los atributos operativos del rol."""
        partes = [self.get_rol_display()]
        if self.especialidad:
            partes.append(self.especialidad)
        if self.zona:
            partes.append(self.zona)
        if self.turno:
            partes.append(self.get_turno_display())
        return " · ".join(partes)


# --------------------------------------------------------------------------- #
#  Insumos y su categoría (3FN: la categoría no se repite en cada insumo)
# --------------------------------------------------------------------------- #
class CategoriaInsumo(models.Model):
    nombre = models.CharField(max_length=60, unique=True)
    descripcion = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Categoría de insumo"
        verbose_name_plural = "Categorías de insumo"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Insumo(models.Model):
    UNIDADES = [
        ("g", "Gramos"),
        ("kg", "Kilogramos"),
        ("ml", "Mililitros"),
        ("l", "Litros"),
        ("un", "Unidad"),
    ]

    nombre = models.CharField(max_length=80, unique=True)
    categoria = models.ForeignKey(
        CategoriaInsumo,
        on_delete=models.PROTECT,
        related_name="insumos",
        null=True,
        blank=True,
    )
    unidad = models.CharField(max_length=5, choices=UNIDADES, default="g")
    stock_actual = models.DecimalField(
        max_digits=10, decimal_places=3, default=Decimal("0")
    )
    stock_minimo = models.DecimalField(
        max_digits=10, decimal_places=3, default=Decimal("0")
    )
    costo_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )
    perecible = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Insumo"
        verbose_name_plural = "Insumos"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.stock_actual} {self.unidad})"

    @property
    def stock_bajo(self):
        return self.stock_actual <= self.stock_minimo


# --------------------------------------------------------------------------- #
#  Productos (recetas) y Lista de Materiales (BOM)
# --------------------------------------------------------------------------- #
class CategoriaProducto(models.Model):
    """Categoría comercial del catálogo (tortas, postres, mesas dulces…)."""

    nombre = models.CharField(max_length=60, unique=True)
    descripcion = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Categoría de producto"
        verbose_name_plural = "Categorías de producto"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    precio_base = models.DecimalField(max_digits=10, decimal_places=2)
    porciones = models.PositiveSmallIntegerField(default=1)
    activo = models.BooleanField(default=True)
    imagen = models.ImageField(upload_to="productos/", blank=True, null=True)
    imagen_estatica = models.CharField(
        max_length=120,
        blank=True,
        help_text=(
            "Imagen de demostración dentro de static/IMAGES "
            "(ej. productos/chocolate.jpg). Se usa si no hay archivo subido."
        ),
    )
    categoria = models.ForeignKey(
        CategoriaProducto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="productos",
    )

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def imagen_url(self):
        """Imagen subida por el admin o, si no hay, la de demostración."""
        from django.templatetags.static import static

        if self.imagen:
            return self.imagen.url
        if self.imagen_estatica:
            ruta = self.imagen_estatica
            if not ruta.startswith("IMAGES/"):
                ruta = f"IMAGES/{ruta}"
            return static(ruta)
        return static("IMAGES/productos/default.jpg")

    @property
    def tiene_imagen(self):
        return bool(self.imagen or self.imagen_estatica)

    @property
    def unidades_disponibles(self):
        """Unidades que se pueden producir con el stock actual (None = sin receta)."""
        ingredientes = [i for i in self.ingredientes.all() if i.cantidad]
        if not ingredientes:
            return None
        return max(
            int(
                min(
                    ingrediente.insumo.stock_actual / ingrediente.cantidad
                    for ingrediente in ingredientes
                )
            ),
            0,
        )

    @property
    def disponible(self):
        disponibles = self.unidades_disponibles
        return disponibles is None or disponibles > 0

    @property
    def costo_estimado(self):
        """Costo de los insumos de la receta (BOM)."""
        return sum(
            (ing.cantidad * ing.insumo.costo_unitario for ing in self.ingredientes.all()),
            Decimal("0"),
        )


class RecetaInsumo(models.Model):
    """Tabla intermedia del BOM: cuánto insumo consume un producto."""

    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name="ingredientes"
    )
    insumo = models.ForeignKey(
        Insumo, on_delete=models.PROTECT, related_name="usos"
    )
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)

    class Meta:
        verbose_name = "Ingrediente de receta"
        verbose_name_plural = "Ingredientes de receta (BOM)"
        ordering = ["producto", "insumo"]
        constraints = [
            models.UniqueConstraint(
                fields=["producto", "insumo"], name="bom_producto_insumo_unico"
            )
        ]

    def __str__(self):
        return f"{self.producto} → {self.cantidad} {self.insumo.unidad} de {self.insumo.nombre}"


# --------------------------------------------------------------------------- #
#  Clientes
# --------------------------------------------------------------------------- #
class Cliente(models.Model):
    """Ficha comercial del cliente.

    Un cliente puede existir sin cuenta (venta de mostrador) o estar vinculado
    a un usuario del sitio para comprar y seguir sus pedidos.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cliente",
    )
    nombre = models.CharField(max_length=120)
    telefono = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    direccion = models.CharField(max_length=200, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.telefono})"

    @property
    def tiene_cuenta(self):
        return self.user_id is not None


# --------------------------------------------------------------------------- #
#  Pedidos (cotización + tablero Kanban)
# --------------------------------------------------------------------------- #
class Pedido(models.Model):
    ESTADOS = [
        ("recibido", "Recibido"),
        ("confirmado", "Confirmado"),
        ("preparacion", "En preparación"),
        ("horneado", "Horneado / Decorado"),
        ("calidad", "Control de calidad"),
        ("listo", "Listo"),
        ("despachado", "Despachado"),
        ("entregado", "Entregado"),
        ("cancelado", "Cancelado"),
    ]

    # Flujo permitido. Producción no arranca hasta que ventas/admin confirma.
    TRANSICIONES = {
        "recibido": ["confirmado", "cancelado"],
        "confirmado": ["preparacion", "cancelado"],
        "preparacion": ["horneado", "cancelado"],
        "horneado": ["calidad", "cancelado"],
        "calidad": ["listo", "preparacion"],
        "listo": ["despachado", "entregado", "cancelado"],
        "despachado": ["entregado"],
        "entregado": [],
        "cancelado": [],
    }

    # Qué rol puede ejecutar cada transición. El admin siempre está incluido.
    TRANSICIONES_ROL = {
        "recibido": {
            "confirmado": ("admin", "ventas"),
            "cancelado": ("admin", "ventas"),
        },
        "confirmado": {
            "preparacion": ("admin", "cocina"),
            "cancelado": ("admin", "ventas"),
        },
        "preparacion": {
            "horneado": ("admin", "cocina"),
            "cancelado": ("admin", "ventas"),
        },
        "horneado": {
            "calidad": ("admin", "cocina"),
            "cancelado": ("admin", "ventas"),
        },
        "calidad": {
            "listo": ("admin", "calidad"),
            "preparacion": ("admin", "calidad", "cocina"),
        },
        "listo": {
            "despachado": ("admin", "despacho", "ventas"),
            "entregado": ("admin", "despacho", "ventas"),
            "cancelado": ("admin", "ventas"),
        },
        "despachado": {"entregado": ("admin", "despacho")},
    }

    CANALES = [
        ("web", "Tienda en línea"),
        ("mostrador", "Mostrador"),
        ("telefono", "Teléfono"),
    ]

    MODALIDADES = [
        ("retiro", "Retiro en tienda"),
        ("despacho", "Despacho a domicilio"),
    ]

    # Reglas comerciales (una pastelería artesanal no produce al instante).
    LEAD_TIME_HORAS = 48
    CUPO_DIARIO = 6
    HORARIO_ATENCION = (9, 19)  # 09:00 a 18:59, hora de Santiago

    codigo = models.CharField(max_length=20, unique=True, blank=True)
    token_seguimiento = models.CharField(
        max_length=24, unique=True, blank=True, null=True
    )
    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name="pedidos"
    )
    canal = models.CharField(max_length=20, choices=CANALES, default="mostrador")
    modalidad = models.CharField(
        max_length=20, choices=MODALIDADES, default="retiro"
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default="recibido")
    fecha_pedido = models.DateTimeField(auto_now_add=True)
    fecha_entrega = models.DateTimeField()
    direccion_entrega = models.CharField(max_length=200, blank=True)
    telefono_contacto = models.CharField(max_length=20, blank=True)
    descripcion_diseno = models.TextField(
        blank=True, help_text="Ingredientes, diseño, colores, temática, etc."
    )
    imagen_referencia = models.ImageField(
        upload_to="referencias/", blank=True, null=True
    )
    anticipo = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    costo_despacho = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )
    observaciones = models.TextField(blank=True)
    retirado_por = models.CharField(max_length=120, blank=True)
    insumos_descontados = models.BooleanField(default=False)
    venta_directa = models.BooleanField(
        default=False,
        help_text=(
            "Venta inmediata de mostrador: descuenta insumos al registrarse y no "
            "ocupa cupo de la agenda."
        ),
    )
    confirmado_en = models.DateTimeField(null=True, blank=True)
    confirmado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos_confirmados",
    )
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos_creados",
    )
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ["-fecha_pedido"]

    def __str__(self):
        return f"{self.codigo or 'nuevo'} · {self.cliente} · {self.get_estado_display()}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        pendientes = []
        if not self.codigo:
            self.codigo = f"PED-{self.pk:05d}"
            pendientes.append("codigo")
        if not self.token_seguimiento:
            token = uuid.uuid4().hex[:12]
            while Pedido.objects.filter(token_seguimiento=token).exists():
                token = uuid.uuid4().hex[:12]
            self.token_seguimiento = token
            pendientes.append("token_seguimiento")
        if pendientes:
            super().save(update_fields=pendientes)

    def clean(self):
        """Valida la agenda: anticipación, horario de atención y cupo diario."""
        super().clean()
        if not self.fecha_entrega:
            return

        if self.modalidad == "despacho" and not (self.direccion_entrega or "").strip():
            raise ValidationError(
                {"direccion_entrega": "Un pedido con despacho necesita dirección."}
            )

        # Una venta de mostrador ocurre ahora: no reserva agenda ni cupo.
        if self.venta_directa:
            return

        self.validar_agenda(
            self.fecha_entrega,
            exigir_anticipacion=self.canal == "web",
            excluir_pk=self.pk,
        )

    @classmethod
    def validar_agenda(cls, fecha_entrega, *, exigir_anticipacion=True, excluir_pk=None):
        """Reglas de agenda compartidas por la tienda y el panel interno."""
        local = timezone.localtime(fecha_entrega)

        if exigir_anticipacion:
            minimo = timezone.localtime() + timedelta(hours=cls.LEAD_TIME_HORAS)
            if local < minimo:
                raise ValidationError(
                    "Los pedidos en línea necesitan al menos "
                    f"{cls.LEAD_TIME_HORAS} horas de anticipación."
                )

        apertura, cierre = cls.HORARIO_ATENCION
        if not (apertura <= local.hour < cierre):
            raise ValidationError(
                f"La entrega debe agendarse entre {apertura:02d}:00 y "
                f"{cierre:02d}:00 (hora de Santiago)."
            )

        agendados = cls.objects.filter(
            venta_directa=False,
            fecha_entrega__gte=local.replace(hour=0, minute=0, second=0, microsecond=0),
            fecha_entrega__lt=local.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            + timedelta(days=1),
        ).exclude(estado="cancelado")
        if excluir_pk:
            agendados = agendados.exclude(pk=excluir_pk)
        if agendados.count() >= cls.CUPO_DIARIO:
            raise ValidationError(
                f"El {local:%d/%m} ya alcanzó el cupo de {cls.CUPO_DIARIO} pedidos. "
                "Elige otra fecha."
            )

    # --------------------------------------------------------- cotización
    @property
    def subtotal_productos(self):
        return sum((d.subtotal for d in self.detalles.all()), Decimal("0"))

    @property
    def total(self):
        return self.subtotal_productos + self.costo_despacho

    @property
    def total_pagado(self):
        """Suma de pagos registrados; usa el anticipo histórico si no hay pagos."""
        pagos = self.pagos.all()
        if pagos:
            return sum((p.monto for p in pagos), Decimal("0"))
        return self.anticipo

    @property
    def saldo(self):
        return self.total - self.total_pagado

    @property
    def estado_pago(self):
        pagado = self.total_pagado
        if pagado <= 0:
            return "pendiente"
        if pagado >= self.total:
            return "pagado"
        return "parcial"

    @property
    def estado_pago_display(self):
        return {
            "pendiente": "Pago pendiente",
            "parcial": "Abono parcial",
            "pagado": "Pagado",
        }[self.estado_pago]

    # ------------------------------------------------------------- kanban
    def transiciones_disponibles(self):
        return [
            (estado, dict(self.ESTADOS)[estado])
            for estado in self.TRANSICIONES.get(self.estado, [])
        ]

    def transiciones_para(self, rol):
        """Transiciones que el rol indicado puede ejecutar desde el estado actual."""
        permitidas = self.TRANSICIONES_ROL.get(self.estado, {})
        return [
            (estado, dict(self.ESTADOS)[estado])
            for estado in self.TRANSICIONES.get(self.estado, [])
            if rol in permitidas.get(estado, ())
            and not (estado == "despachado" and self.modalidad != "despacho")
        ]

    @transaction.atomic
    def descontar_insumos(self, usuario=None):
        """Descuenta del inventario los insumos que consume el pedido (BOM)."""
        if self.insumos_descontados:
            return

        requeridos = {}
        for detalle in self.detalles.select_related("producto"):
            for ingrediente in detalle.producto.ingredientes.select_related("insumo"):
                requeridos[ingrediente.insumo_id] = (
                    requeridos.get(ingrediente.insumo_id, Decimal("0"))
                    + ingrediente.cantidad * detalle.cantidad
                )

        insumos = {
            i.pk: i
            for i in Insumo.objects.select_for_update().filter(pk__in=requeridos)
        }

        faltantes = [
            f"{insumos[pk].nombre}: se necesitan {cantidad} {insumos[pk].unidad} "
            f"y hay {insumos[pk].stock_actual}"
            for pk, cantidad in requeridos.items()
            if insumos[pk].stock_actual < cantidad
        ]
        if faltantes:
            raise ValidationError("Stock insuficiente → " + "; ".join(faltantes))

        for pk, cantidad in requeridos.items():
            insumo = insumos[pk]
            insumo.stock_actual -= cantidad
            insumo.save(update_fields=["stock_actual"])
            MovimientoInsumo.objects.create(
                insumo=insumo,
                tipo="consumo",
                cantidad=cantidad,
                pedido=self,
                usuario=usuario,
                observacion=f"Consumo por producción del pedido {self.codigo}",
            )

        self.insumos_descontados = True
        self.save(update_fields=["insumos_descontados"])

    @transaction.atomic
    def reponer_insumos(self, usuario=None):
        """Devuelve al inventario lo consumido si el pedido se cancela."""
        if not self.insumos_descontados:
            return

        consumos = self.movimientos.filter(tipo="consumo").select_related("insumo")
        for consumo in consumos:
            insumo = Insumo.objects.select_for_update().get(pk=consumo.insumo_id)
            insumo.stock_actual += consumo.cantidad
            insumo.save(update_fields=["stock_actual"])
            MovimientoInsumo.objects.create(
                insumo=insumo,
                tipo="entrada",
                cantidad=consumo.cantidad,
                pedido=self,
                usuario=usuario,
                observacion=f"Reposición por cancelación del pedido {self.codigo}",
            )

        self.insumos_descontados = False
        self.save(update_fields=["insumos_descontados"])

    @transaction.atomic
    def cambiar_estado(
        self, nuevo_estado, usuario=None, comentario="", *, venta_directa=False
    ):
        """Mueve el pedido por el flujo validando reglas de negocio.

        `venta_directa=True` habilita la ruta express de una venta de mostrador:
        desde `recibido` el pedido puede cerrarse como `entregado` (el cliente se
        lo lleva) o `despachado` (sale a delivery), descontando insumos una vez.
        """
        if nuevo_estado == self.estado:
            raise ValidationError("El pedido ya se encuentra en ese estado.")

        venta_inmediata = (
            venta_directa
            and self.venta_directa
            and self.estado == "recibido"
            and nuevo_estado in {"despachado", "entregado"}
        )

        if (
            nuevo_estado not in self.TRANSICIONES.get(self.estado, [])
            and not venta_inmediata
        ):
            raise ValidationError(
                f"Transición no permitida: {self.get_estado_display()} → "
                f"{dict(self.ESTADOS).get(nuevo_estado, nuevo_estado)}."
            )

        if usuario is not None:
            from .roles import rol_de

            rol = rol_de(usuario)
            if venta_inmediata:
                if rol not in ("admin", "ventas"):
                    raise ValidationError(
                        "Solo ventas o administración pueden cerrar una venta de "
                        "mostrador."
                    )
            else:
                roles_permitidos = self.TRANSICIONES_ROL.get(self.estado, {}).get(
                    nuevo_estado
                )
                if roles_permitidos is not None and rol not in roles_permitidos:
                    raise ValidationError(
                        "Tu rol no puede mover el pedido de "
                        f"{self.get_estado_display()} a "
                        f"{dict(self.ESTADOS).get(nuevo_estado, nuevo_estado)}. "
                        "Esta acción corresponde a otro equipo."
                    )

        if nuevo_estado == "confirmado":
            if self.estado_pago == "pendiente":
                raise ValidationError(
                    "Confirma el pago del anticipo antes de pasar el pedido a "
                    "producción."
                )

        if nuevo_estado == "despachado" and self.modalidad != "despacho":
            raise ValidationError(
                "Solo un pedido con despacho a domicilio puede salir a reparto."
            )

        if nuevo_estado in {"despachado", "entregado"}:
            despacho = Despacho.objects.filter(pedido=self).first()
            if self.modalidad == "despacho":
                if not despacho and nuevo_estado == "despachado":
                    if not (self.direccion_entrega or "").strip():
                        raise ValidationError(
                            "Un pedido con despacho necesita una dirección de "
                            "entrega."
                        )
                    despacho = Despacho.objects.create(
                        pedido=self,
                        direccion=self.direccion_entrega,
                        fecha_salida=timezone.now(),
                        observaciones=(
                            "Ruta creada al marcar el pedido como despachado."
                        ),
                    )
                if not despacho:
                    raise ValidationError(
                        "Asigna un despacho antes de mover el pedido a reparto."
                    )
                if nuevo_estado == "despachado" and not despacho.fecha_salida:
                    despacho.fecha_salida = timezone.now()
                    despacho.save(update_fields=["fecha_salida"])
                if nuevo_estado == "entregado" and not despacho.confirmado:
                    raise ValidationError(
                        "Para marcar el pedido como entregado debes confirmar un "
                        "despacho con firma o comprobante."
                    )
            elif nuevo_estado == "entregado" and not (self.retirado_por or "").strip():
                raise ValidationError(
                    "Registra quién retira el pedido antes de cerrarlo."
                )

        if nuevo_estado == "preparacion" or venta_inmediata:
            self.descontar_insumos(usuario)

        if nuevo_estado == "cancelado":
            self.reponer_insumos(usuario)

        estado_anterior = self.estado
        campos = ["estado", "actualizado"]
        self.estado = nuevo_estado
        if nuevo_estado == "confirmado":
            self.confirmado_en = timezone.now()
            self.confirmado_por = usuario
            campos += ["confirmado_en", "confirmado_por"]
        self.save(update_fields=campos)

        HistorialEstado.objects.create(
            pedido=self,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            usuario=usuario,
            comentario=comentario,
        )
        return self


class PedidoDetalle(models.Model):
    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE, related_name="detalles"
    )
    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT, related_name="detalles"
    )
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    personalizacion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Detalle de pedido"
        verbose_name_plural = "Detalles de pedido"

    def __str__(self):
        return f"{self.cantidad} x {self.producto}"

    def save(self, *args, **kwargs):
        if self.precio_unitario is None:
            self.precio_unitario = self.producto.precio_base
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return (self.precio_unitario or Decimal("0")) * self.cantidad


class HistorialEstado(models.Model):
    """Trazabilidad: cada movimiento del pedido en el Kanban."""

    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE, related_name="historial"
    )
    estado_anterior = models.CharField(max_length=20, choices=Pedido.ESTADOS, blank=True)
    estado_nuevo = models.CharField(max_length=20, choices=Pedido.ESTADOS)
    usuario = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    comentario = models.CharField(max_length=200, blank=True)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Historial de estado"
        verbose_name_plural = "Historial de estados"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.pedido.codigo}: {self.estado_anterior} → {self.estado_nuevo}"


# --------------------------------------------------------------------------- #
#  Movimientos de inventario (auditoría del BOM)
# --------------------------------------------------------------------------- #
class MovimientoInsumo(models.Model):
    TIPOS = [
        ("entrada", "Entrada de stock"),
        ("consumo", "Consumo por producción"),
        ("ajuste", "Ajuste de inventario"),
    ]

    insumo = models.ForeignKey(
        Insumo, on_delete=models.CASCADE, related_name="movimientos"
    )
    tipo = models.CharField(max_length=20, choices=TIPOS)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos",
    )
    usuario = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    fecha = models.DateTimeField(default=timezone.now)
    observacion = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Movimiento de insumo"
        verbose_name_plural = "Movimientos de insumos"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.get_tipo_display()} · {self.insumo} · {self.cantidad}"


# --------------------------------------------------------------------------- #
#  Pagos (registro manual: efectivo, transferencia, tarjeta)
# --------------------------------------------------------------------------- #
class Pago(models.Model):
    """Abono real recibido. El estado de pago del pedido se calcula desde aquí."""

    METODOS = [
        ("efectivo", "Efectivo"),
        ("transferencia", "Transferencia bancaria"),
        ("tarjeta", "Tarjeta débito/crédito"),
    ]
    TIPOS = [
        ("anticipo", "Anticipo"),
        ("saldo", "Saldo final"),
        ("completo", "Pago completo"),
    ]

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="pagos")
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo = models.CharField(max_length=20, choices=METODOS, default="transferencia")
    tipo = models.CharField(max_length=20, choices=TIPOS, default="anticipo")
    referencia = models.CharField(
        max_length=100, blank=True, help_text="N° de transferencia o voucher."
    )
    registrado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="pagos"
    )
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.pedido.codigo} · ${self.monto} · {self.get_metodo_display()}"

    def clean(self):
        if self.monto is not None and self.monto <= 0:
            raise ValidationError({"monto": "El monto debe ser mayor que cero."})


# --------------------------------------------------------------------------- #
#  Despacho y confirmación de entrega
# --------------------------------------------------------------------------- #
class Despacho(models.Model):
    pedido = models.OneToOneField(
        Pedido, on_delete=models.CASCADE, related_name="despacho"
    )
    repartidor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="despachos"
    )
    direccion = models.CharField(max_length=200)
    fecha_salida = models.DateTimeField(null=True, blank=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    receptor_nombre = models.CharField(max_length=120, blank=True)
    confirmado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="despachos_confirmados",
    )
    firma = models.ImageField(upload_to="firmas/", blank=True, null=True)
    comprobante = models.ImageField(upload_to="comprobantes/", blank=True, null=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = "Despacho"
        verbose_name_plural = "Despachos"
        ordering = ["-fecha_salida"]

    def __str__(self):
        return f"Despacho {self.pedido.codigo} → {self.direccion}"

    @property
    def confirmado(self):
        return bool(self.fecha_entrega and (self.firma or self.comprobante))

    def clean(self):
        if self.fecha_entrega:
            if not (self.firma or self.comprobante):
                raise ValidationError(
                    "Para confirmar la entrega debes adjuntar la firma digital "
                    "o el comprobante fotográfico."
                )
            if not (self.receptor_nombre or "").strip():
                raise ValidationError("Debes indicar quién recibe la entrega.")

        if self._state.adding and self.pedido_id:
            if self.pedido.estado != "listo" and not self.pedido.venta_directa:
                raise ValidationError(
                    "Solo se puede crear un despacho para un pedido en estado Listo."
                )


# --------------------------------------------------------------------------- #
#  Contacto (formulario del sitio)
# --------------------------------------------------------------------------- #
class MensajeContacto(models.Model):
    nombre = models.CharField(max_length=120)
    email = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True)
    mensaje = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    atendido = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Mensaje de contacto"
        verbose_name_plural = "Mensajes de contacto"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.nombre} · {self.email}"
