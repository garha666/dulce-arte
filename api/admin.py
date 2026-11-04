"""Panel de administración personalizado de Dulce Arte."""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    CategoriaInsumo,
    Cliente,
    Despacho,
    HistorialEstado,
    Insumo,
    MensajeContacto,
    MovimientoInsumo,
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
#  Usuarios
# --------------------------------------------------------------------------- #
@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("user", "rol", "telefono")
    list_filter = ("rol",)
    search_fields = ("user__username", "user__first_name", "user__last_name")
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


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "precio_base", "porciones", "costo_estimado", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre", "descripcion")
    inlines = [RecetaInsumoInline]
    list_editable = ("activo",)

    @admin.display(description="Costo insumos")
    def costo_estimado(self, obj):
        return f"${obj.costo_estimado:,.0f}"


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
        "estado",
        "fecha_entrega",
        "total_pedido",
        "saldo_pedido",
        "insumos_descontados",
    )
    list_filter = ("estado", "insumos_descontados", "fecha_entrega")
    search_fields = ("codigo", "cliente__nombre", "descripcion_diseno")
    date_hierarchy = "fecha_entrega"
    readonly_fields = ("codigo", "fecha_pedido", "actualizado", "total_pedido", "saldo_pedido")
    inlines = [PedidoDetalleInline, HistorialEstadoInline]
    list_select_related = ("cliente",)
    list_per_page = 20
    actions = ("marcar_listo",)

    fieldsets = (
        ("Identificación", {"fields": ("codigo", "cliente", "estado", "creado_por")}),
        ("Entrega", {"fields": ("fecha_pedido", "fecha_entrega")}),
        ("Diseño del pedido", {"fields": ("descripcion_diseno", "imagen_referencia", "observaciones")}),
        ("Montos", {"fields": ("anticipo", "costo_despacho", "total_pedido", "saldo_pedido")}),
    )

    @admin.display(description="Total")
    def total_pedido(self, obj):
        return f"${obj.total:,.0f}"

    @admin.display(description="Saldo")
    def saldo_pedido(self, obj):
        return f"${obj.saldo:,.0f}"

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


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "telefono", "email", "direccion", "pedidos_count")
    search_fields = ("nombre", "telefono", "email")
    list_per_page = 25

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
        "confirmado",
    )
    list_filter = ("fecha_entrega", "repartidor")
    search_fields = ("pedido__codigo", "direccion", "receptor_nombre")
    date_hierarchy = "fecha_salida"
    list_select_related = ("pedido", "repartidor")

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
