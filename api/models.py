"""
Modelos del dominio: Dulce Arte (pastelería artesanal).

Diseño en Tercera Forma Normal (3FN):
  - 1FN: todos los campos son atómicos (sin listas ni campos compuestos).
  - 2FN: cada atributo depende de la PK de su propia tabla.
  - 3FN: los datos de una entidad no se repiten en otra tabla:
         la relación receta <-> insumo vive en la tabla intermedia RecetaInsumo
         (equivalente al ejemplo libro-autor-editorial de la unidad de BD).
"""

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
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="perfil"
    )
    rol = models.CharField(max_length=20, choices=ROLES, default="ventas")
    telefono = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "Perfil de usuario"
        verbose_name_plural = "Perfiles de usuario"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_rol_display()})"


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
class Producto(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    precio_base = models.DecimalField(max_digits=10, decimal_places=2)
    porciones = models.PositiveSmallIntegerField(default=1)
    activo = models.BooleanField(default=True)
    imagen = models.ImageField(upload_to="productos/", blank=True, null=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

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


# --------------------------------------------------------------------------- #
#  Pedidos (cotización + tablero Kanban)
# --------------------------------------------------------------------------- #
class Pedido(models.Model):
    ESTADOS = [
        ("recibido", "Recibido"),
        ("preparacion", "En preparación"),
        ("horneado", "Horneado / Decorado"),
        ("calidad", "Control de calidad"),
        ("listo", "Listo"),
        ("despachado", "Despachado"),
        ("entregado", "Entregado"),
        ("cancelado", "Cancelado"),
    ]

    # Flujo permitido del tablero Kanban
    TRANSICIONES = {
        "recibido": ["preparacion", "cancelado"],
        "preparacion": ["horneado", "cancelado"],
        "horneado": ["calidad", "cancelado"],
        "calidad": ["listo", "preparacion"],
        "listo": ["despachado", "entregado"],
        "despachado": ["entregado"],
        "entregado": [],
        "cancelado": [],
    }

    codigo = models.CharField(max_length=20, unique=True, blank=True)
    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name="pedidos"
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default="recibido")
    fecha_pedido = models.DateTimeField(auto_now_add=True)
    fecha_entrega = models.DateTimeField()
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
    insumos_descontados = models.BooleanField(default=False)
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
        if not self.codigo:
            self.codigo = f"PED-{self.pk:05d}"
            super().save(update_fields=["codigo"])

    # --------------------------------------------------------- cotización
    @property
    def subtotal_productos(self):
        return sum((d.subtotal for d in self.detalles.all()), Decimal("0"))

    @property
    def total(self):
        return self.subtotal_productos + self.costo_despacho

    @property
    def saldo(self):
        return self.total - self.anticipo

    # ------------------------------------------------------------- kanban
    def transiciones_disponibles(self):
        return [
            (estado, dict(self.ESTADOS)[estado])
            for estado in self.TRANSICIONES.get(self.estado, [])
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
    def cambiar_estado(self, nuevo_estado, usuario=None, comentario=""):
        """Mueve el pedido en el tablero Kanban validando el flujo."""
        if nuevo_estado == self.estado:
            raise ValidationError("El pedido ya se encuentra en ese estado.")

        if nuevo_estado not in self.TRANSICIONES.get(self.estado, []):
            raise ValidationError(
                f"Transición no permitida: {self.get_estado_display()} → "
                f"{dict(self.ESTADOS).get(nuevo_estado, nuevo_estado)}."
            )

        if nuevo_estado == "preparacion":
            self.descontar_insumos(usuario)

        estado_anterior = self.estado
        self.estado = nuevo_estado
        self.save(update_fields=["estado", "actualizado"])

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
        if self.fecha_entrega and not (self.firma or self.comprobante):
            raise ValidationError(
                "Para confirmar la entrega debes adjuntar la firma digital "
                "o el comprobante fotográfico."
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
