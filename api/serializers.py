"""Serializers de la API DRF de Dulce Arte."""

from rest_framework import serializers

from .models import (
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


class PerfilSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    rol_display = serializers.CharField(source="get_rol_display", read_only=True)

    class Meta:
        model = Perfil
        fields = ("id", "username", "rol", "rol_display", "telefono")


class InsumoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    unidad_display = serializers.CharField(source="get_unidad_display", read_only=True)
    stock_bajo = serializers.BooleanField(read_only=True)

    class Meta:
        model = Insumo
        fields = (
            "id",
            "nombre",
            "categoria",
            "categoria_nombre",
            "unidad",
            "unidad_display",
            "stock_actual",
            "stock_minimo",
            "costo_unitario",
            "perecible",
            "stock_bajo",
        )


class RecetaInsumoSerializer(serializers.ModelSerializer):
    insumo_nombre = serializers.CharField(source="insumo.nombre", read_only=True)
    unidad = serializers.CharField(source="insumo.unidad", read_only=True)

    class Meta:
        model = RecetaInsumo
        fields = ("id", "insumo", "insumo_nombre", "unidad", "cantidad")


class ProductoSerializer(serializers.ModelSerializer):
    ingredientes = RecetaInsumoSerializer(many=True, required=False)
    costo_estimado = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = Producto
        fields = (
            "id",
            "nombre",
            "descripcion",
            "precio_base",
            "porciones",
            "activo",
            "imagen",
            "ingredientes",
            "costo_estimado",
        )

    def create(self, validated_data):
        ingredientes = validated_data.pop("ingredientes", [])
        producto = Producto.objects.create(**validated_data)
        for ingrediente in ingredientes:
            RecetaInsumo.objects.create(producto=producto, **ingrediente)
        return producto

    def update(self, instance, validated_data):
        ingredientes = validated_data.pop("ingredientes", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()
        if ingredientes is not None:
            instance.ingredientes.all().delete()
            for ingrediente in ingredientes:
                RecetaInsumo.objects.create(producto=instance, **ingrediente)
        return instance


class PedidoDetalleSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = PedidoDetalle
        fields = (
            "id",
            "producto",
            "producto_nombre",
            "cantidad",
            "precio_unitario",
            "personalizacion",
            "subtotal",
        )


class HistorialEstadoSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source="usuario.username", read_only=True)

    class Meta:
        model = HistorialEstado
        fields = (
            "id",
            "estado_anterior",
            "estado_nuevo",
            "usuario_nombre",
            "comentario",
            "fecha",
        )


class DespachoSerializer(serializers.ModelSerializer):
    pedido_codigo = serializers.CharField(source="pedido.codigo", read_only=True)
    confirmado = serializers.BooleanField(read_only=True)

    class Meta:
        model = Despacho
        fields = (
            "id",
            "pedido",
            "pedido_codigo",
            "repartidor",
            "direccion",
            "fecha_salida",
            "fecha_entrega",
            "receptor_nombre",
            "firma",
            "comprobante",
            "observaciones",
            "confirmado",
        )

    def validate(self, datos):
        pedido = datos.get("pedido", getattr(self.instance, "pedido", None))
        if self.instance is None and pedido and pedido.estado != "listo":
            raise serializers.ValidationError(
                {
                    "pedido": (
                        "Solo se puede crear un despacho para un pedido "
                        "en estado Listo."
                    )
                }
            )

        fecha_entrega = datos.get(
            "fecha_entrega", getattr(self.instance, "fecha_entrega", None)
        )
        firma = datos.get("firma", getattr(self.instance, "firma", None))
        comprobante = datos.get("comprobante", getattr(self.instance, "comprobante", None))
        receptor = datos.get(
            "receptor_nombre", getattr(self.instance, "receptor_nombre", "")
        )

        if fecha_entrega and not (firma or comprobante):
            raise serializers.ValidationError(
                "Para confirmar la entrega debes adjuntar firma digital o comprobante."
            )
        if fecha_entrega and not (receptor or "").strip():
            raise serializers.ValidationError(
                {"receptor_nombre": "Debes indicar quién recibe la entrega."}
            )
        return datos


class PedidoSerializer(serializers.ModelSerializer):
    detalles = PedidoDetalleSerializer(many=True, required=False)
    cliente_nombre = serializers.CharField(source="cliente.nombre", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    saldo = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    historial = HistorialEstadoSerializer(many=True, read_only=True)

    class Meta:
        model = Pedido
        fields = (
            "id",
            "codigo",
            "cliente",
            "cliente_nombre",
            "estado",
            "estado_display",
            "fecha_pedido",
            "fecha_entrega",
            "descripcion_diseno",
            "imagen_referencia",
            "anticipo",
            "costo_despacho",
            "observaciones",
            "insumos_descontados",
            "total",
            "saldo",
            "detalles",
            "historial",
        )
        read_only_fields = ("codigo", "fecha_pedido", "insumos_descontados", "estado")

    def validate(self, datos):
        # RF-4: un pedido nuevo debe incluir al menos un producto.
        if self.instance is None and not datos.get("detalles"):
            raise serializers.ValidationError(
                {"detalles": "El pedido debe incluir al menos un producto."}
            )
        return datos

    def create(self, validated_data):
        detalles = validated_data.pop("detalles", [])
        pedido = Pedido.objects.create(**validated_data)
        for detalle in detalles:
            PedidoDetalle.objects.create(pedido=pedido, **detalle)
        return pedido

    def update(self, instance, validated_data):
        if instance.insumos_descontados:
            raise serializers.ValidationError(
                "No se puede modificar un pedido cuyos insumos ya fueron "
                "descontados del inventario."
            )

        detalles = validated_data.pop("detalles", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()
        if detalles is not None:
            instance.detalles.all().delete()
            for detalle in detalles:
                PedidoDetalle.objects.create(pedido=instance, **detalle)
        return instance


class MovimientoInsumoSerializer(serializers.ModelSerializer):
    insumo_nombre = serializers.CharField(source="insumo.nombre", read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = MovimientoInsumo
        fields = (
            "id",
            "insumo",
            "insumo_nombre",
            "tipo",
            "tipo_display",
            "cantidad",
            "pedido",
            "usuario",
            "fecha",
            "observacion",
        )


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = "__all__"


class MensajeContactoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MensajeContacto
        fields = "__all__"
        read_only_fields = ("fecha", "atendido")
