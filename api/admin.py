"""Panel de administración personalizado de Dulce Arte."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html

from .models import (
    CategoriaInsumo,
    CategoriaProducto,
    Cliente,
    Despacho,
    HistorialEstado,
    Insumo,
    MensajeContacto,
    MovimientoInsumo,
    Pago,
    Pedido,
    PedidoDetalle,
    Perfil,
    Producto,
    RecetaInsumo,
)

# --------------------------------------------------------------------------- #
#  Personalización de la cabecera del Admin
# --------------------------------------------------------------------------- #
admin.site.site_header = "Dulce Arte · Administración"
admin.site.site_title = "Dulce Arte"
admin.site.index_title = "Panel de gestión de la pastelería"


# --------------------------------------------------------------------------- #
#  Usuarios: cuenta + perfil (rol y atributos) en una sola pantalla
# --------------------------------------------------------------------------- #
class PerfilInline(admin.StackedInline):
    model = Perfil
    can_delete = False
    extra = 1
    max_num = 1
    verbose_name_plural = "Perfil, rol y atributos"
    fields = (
        "rol",
        "telefono",
        "turno",
        "especialidad",
        "zona",
        "vehiculo",
        "notas",
    )


if admin.site.is_registered(User):
    admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [PerfilInline]
    list_display = (
        "username",
        "nombre_completo",
        "email",
        "rol_mostrado",
        "is_active",
        "is_staff",
    )
    list_filter = BaseUserAdmin.list_filter + ("perfil__rol", "perfil__turno")
    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "perfil__telefono",
        "perfil__especialidad",
    )
    list_select_related = ("perfil",)
    list_per_page = 25
    actions = ("activar_usuarios", "desactivar_usuarios")

    @admin.display(description="Nombre")
    def nombre_completo(self, obj):
        return obj.get_full_name() or "—"

    @admin.display(description="Rol", ordering="perfil__rol")
    def rol_mostrado(self, obj):
        perfil = getattr(obj, "perfil", None)
        return perfil.get_rol_display() if perfil else "Sin perfil"

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        Perfil.objects.get_or_create(
            user=form.instance, defaults={"rol": "cliente"}
        )

    @admin.action(description="Activar las cuentas seleccionadas")
    def activar_usuarios(self, request, queryset):
        actualizados = queryset.update(is_active=True)
        self.message_user(request, f"{actualizados} cuenta(s) activadas.")

    @admin.action(description="Desactivar las cuentas seleccionadas")
    def desactivar_usuarios(self, request, queryset):
        actualizados = queryset.exclude(pk=request.user.pk).update(is_active=False)
        self.message_user(request, f"{actualizados} cuenta(s) desactivadas.")


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "rol",
        "telefono",
        "turno",
        "especialidad",
        "zona",
        "vehiculo",
    )
    list_filter = ("rol", "turno")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "especialidad",
        "zona",
    )
    list_select_related = ("user",)


# --------------------------------------------------------------------------- #
#  Insumos
# --------------------------------------------------------------------------- #
@admin.register(CategoriaInsumo)
class CategoriaInsumoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion", "cantidad_insumos")
    search_fields = ("nombre",)

    @admin.display(description="Insumos")
    def cantidad_insumos(self, obj):
        return obj.insumos.count()


@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "categoria",
        "stock_actual",
        "unidad",
        "stock_minimo",
        "costo_unitario",
        "perecible",
        "alerta_stock",
    )
    list_filter = ("categoria", "unidad", "perecible")
    search_fields = ("nombre",)
    list_editable = ("stock_actual",)
    list_per_page = 25
    ordering = ("nombre",)

    @admin.display(description="Estado stock", boolean=True)
    def alerta_stock(self, obj):
        return obj.stock_bajo


@admin.register(MovimientoInsumo)
class MovimientoInsumoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "insumo", "tipo", "cantidad", "pedido", "usuario")
    list_filter = ("tipo", "fecha", "insumo__categoria")
    search_fields = ("insumo__nombre", "pedido__codigo", "observacion")
    date_hierarchy = "fecha"
    readonly_fields = ("fecha",)
    list_select_related = ("insumo", "pedido", "usuario")


# --------------------------------------------------------------------------- #
#  Productos y BOM
# --------------------------------------------------------------------------- #
class RecetaInsumoInline(admin.TabularInline):
    model = RecetaInsumo
    extra = 1
    autocomplete_fields = ("insumo",)


@admin.register(CategoriaProducto)
class CategoriaProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion", "cantidad_productos")
    search_fields = ("nombre",)

    @admin.display(description="Productos")
    def cantidad_productos(self, obj):
        return obj.productos.count()


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        "miniatura",
        "nombre",
        "categoria",
        "precio_base",
        "porciones",
        "costo_estimado",
        "unidades_disponibles",
        "activo",
    )
    list_filter = ("activo", "categoria")
    search_fields = ("nombre", "descripcion")
    inlines = [RecetaInsumoInline]
    list_editable = ("activo",)
    readonly_fields = ("miniatura",)
    fieldsets = (
        (
            "Producto",
            {
                "fields": (
                    "nombre",
                    "categoria",
                    "descripcion",
                    "precio_base",
                    "porciones",
                    "activo",
                )
            },
        ),
        (
            "Imagen del catálogo",
            {
                "fields": ("miniatura", "imagen", "imagen_estatica"),
                "description": (
                    "Sube una foto propia o usa una imagen de demostración de "
                    "static/IMAGES. La imagen subida tiene prioridad."
                ),
            },
        ),
    )

    @admin.display(description="Imagen")
    def miniatura(self, obj):
        if not obj or not obj.pk:
            return "—"
        return format_html(
            '<img src="{}" alt="{}" '
            'style="height:52px;width:68px;object-fit:cover;'
            'border-radius:8px;border:1px solid #e8d8c6;">',
            obj.imagen_url,
            obj.nombre,
        )

    @admin.display(description="Costo insumos")
    def costo_estimado(self, obj):
        return f"${obj.costo_estimado:,.0f}"

    @admin.display(description="Se pueden producir")
    def unidades_disponibles(self, obj):
        disponibles = obj.unidades_disponibles
        return "sin receta" if disponibles is None else disponibles


# --------------------------------------------------------------------------- #
#  Pedidos
# --------------------------------------------------------------------------- #
class PedidoDetalleInline(admin.TabularInline):
    model = PedidoDetalle
    extra = 1
    autocomplete_fields = ("producto",)
    readonly_fields = ("subtotal",)

    @admin.display(description="Subtotal")
    def subtotal(self, obj):
        return f"${obj.subtotal:,.0f}" if obj.pk else "—"


class HistorialEstadoInline(admin.TabularInline):
    model = HistorialEstado
    extra = 0
    can_delete = False
    readonly_fields = ("estado_anterior", "estado_nuevo", "usuario", "comentario", "fecha")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "cliente",
        "canal",
        "modalidad",
        "estado",
        "estado_pago",
        "fecha_entrega",
        "total_pedido",
        "saldo_pedido",
        "venta_directa",
        "insumos_descontados",
    )
    list_filter = ("estado", "canal", "modalidad", "venta_directa", "insumos_descontados", "fecha_entrega")
    search_fields = ("codigo", "cliente__nombre", "descripcion_diseno", "token_seguimiento")
    date_hierarchy = "fecha_entrega"
    readonly_fields = (
        "codigo",
        "token_seguimiento",
        "fecha_pedido",
        "actualizado",
        "estado",
        "total_pedido",
        "saldo_pedido",
        "estado_pago",
        "venta_directa",
    )
    inlines = [PedidoDetalleInline, HistorialEstadoInline]
    list_select_related = ("cliente",)
    list_per_page = 20
    actions = ("marcar_listo", "confirmar_pedidos")

    fieldsets = (
        (
            "Identificación",
            {
                "fields": (
                    "codigo",
                    "token_seguimiento",
                    "cliente",
                    "canal",
                    "venta_directa",
                    "estado",
                    "creado_por",
                    "confirmado_por",
                    "confirmado_en",
                )
            },
        ),
        (
            "Entrega",
            {
                "fields": (
                    "modalidad",
                    "fecha_pedido",
                    "fecha_entrega",
                    "direccion_entrega",
                    "telefono_contacto",
                    "retirado_por",
                )
            },
        ),
        (
            "Diseño del pedido",
            {"fields": ("descripcion_diseno", "imagen_referencia", "observaciones")},
        ),
        (
            "Montos",
            {
                "fields": (
                    "anticipo",
                    "costo_despacho",
                    "total_pedido",
                    "saldo_pedido",
                    "estado_pago",
                )
            },
        ),
    )

    @admin.display(description="Total")
    def total_pedido(self, obj):
        return f"${obj.total:,.0f}"

    @admin.display(description="Saldo")
    def saldo_pedido(self, obj):
        return f"${obj.saldo:,.0f}"

    @admin.display(description="Estado pago")
    def estado_pago(self, obj):
        return obj.estado_pago_display

    @admin.action(description="Pasar los pedidos seleccionados a 'Listo'")
    def marcar_listo(self, request, queryset):
        actualizados = 0
        for pedido in queryset:
            try:
                pedido.cambiar_estado("listo", usuario=request.user)
                actualizados += 1
            except Exception:
                continue
        self.message_user(request, f"{actualizados} pedido(s) marcados como Listo.")

    @admin.action(description="Confirmar los pedidos seleccionados")
    def confirmar_pedidos(self, request, queryset):
        actualizados = 0
        for pedido in queryset.filter(estado="recibido"):
            try:
                pedido.cambiar_estado("confirmado", usuario=request.user)
                actualizados += 1
            except Exception:
                continue
        self.message_user(request, f"{actualizados} pedido(s) confirmados.")


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "pedido", "monto", "metodo", "tipo", "registrado_por")
    list_filter = ("metodo", "tipo", "fecha")
    search_fields = ("pedido__codigo", "referencia")
    date_hierarchy = "fecha"
    list_select_related = ("pedido", "registrado_por")


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "telefono",
        "email",
        "user",
        "tiene_cuenta",
        "direccion",
        "pedidos_count",
    )
    list_filter = ("user__is_active",)
    search_fields = ("nombre", "telefono", "email", "user__username")
    list_select_related = ("user",)
    list_per_page = 25
    autocomplete_fields = ("user",)

    @admin.display(description="Cuenta", boolean=True)
    def tiene_cuenta(self, obj):
        return obj.tiene_cuenta

    @admin.display(description="Pedidos")
    def pedidos_count(self, obj):
        return obj.pedidos.count()


@admin.register(Despacho)
class DespachoAdmin(admin.ModelAdmin):
    list_display = (
        "pedido",
        "direccion",
        "repartidor",
        "fecha_salida",
        "fecha_entrega",
        "confirmado_por",
        "confirmado",
    )
    list_filter = ("fecha_entrega", "repartidor")
    search_fields = ("pedido__codigo", "direccion", "receptor_nombre")
    date_hierarchy = "fecha_salida"
    list_select_related = ("pedido", "repartidor", "confirmado_por")

    @admin.display(description="Confirmado", boolean=True)
    def confirmado(self, obj):
        return obj.confirmado


@admin.register(MensajeContacto)
class MensajeContactoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "nombre", "email", "telefono", "atendido")
    list_filter = ("atendido", "fecha")
    search_fields = ("nombre", "email", "mensaje")
    list_editable = ("atendido",)
    readonly_fields = ("fecha",)


admin.site.register(HistorialEstado)
