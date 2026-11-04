"""
Datos de prueba para Dulce Arte.
Uso:  python seed_data.py
"""

import os
from datetime import timedelta
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "drf.settings")
django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.utils import timezone  # noqa: E402

from api.models import (  # noqa: E402
    CategoriaInsumo,
    Cliente,
    HistorialEstado,
    Insumo,
    Pedido,
    PedidoDetalle,
    Perfil,
    Producto,
    RecetaInsumo,
)

CLAVE = "Dulce2026!"

USUARIOS = [
    ("admin", "Administrador", "Dulce Arte", "admin"),
    ("ventas", "Vendedor", "Mostrador", "ventas"),
    ("cocina", "Jefa", "de Cocina", "cocina"),
    ("calidad", "Control", "de Calidad", "calidad"),
    ("despacho", "Repartidor", "Zona Centro", "despacho"),
]


def crear_usuarios():
    for username, nombre, apellido, rol in USUARIOS:
        user, creado = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": nombre,
                "last_name": apellido,
                "email": f"{username}@dulcearte.cl",
                "is_staff": rol == "admin",
                "is_superuser": rol == "admin",
            },
        )
        if creado:
            user.set_password(CLAVE)
            user.save()
        Perfil.objects.get_or_create(user=user, defaults={"rol": rol})


def crear_insumos():
    categorias = {}
    for nombre in ["Masas", "Cremas", "Decoración", "Frutas", "Empaque"]:
        categorias[nombre], _ = CategoriaInsumo.objects.get_or_create(nombre=nombre)

    datos = [
        ("Harina sin polvos", "Masas", "g", "12000", "2000", "1.2", False),
        ("Azúcar", "Masas", "g", "9000", "1500", "1.0", False),
        ("Mantequilla", "Cremas", "g", "4500", "1000", "8.5", True),
        ("Huevos", "Cremas", "un", "60", "24", "280", True),
        ("Crema para batir", "Cremas", "ml", "3000", "1000", "4.2", True),
        ("Chocolate cobertura", "Decoración", "g", "2500", "800", "12.0", False),
        ("Frutillas", "Frutas", "g", "1800", "500", "6.5", True),
        ("Colorante vegetal", "Decoración", "ml", "300", "100", "18.0", False),
        ("Caja para torta", "Empaque", "un", "40", "15", "950", False),
        ("Manjar", "Cremas", "g", "3500", "800", "5.4", True),
    ]
    insumos = {}
    for nombre, categoria, unidad, stock, minimo, costo, perecible in datos:
        insumo, _ = Insumo.objects.get_or_create(
            nombre=nombre,
            defaults={
                "categoria": categorias[categoria],
                "unidad": unidad,
                "stock_actual": Decimal(stock),
                "stock_minimo": Decimal(minimo),
                "costo_unitario": Decimal(costo),
                "perecible": perecible,
            },
        )
        insumos[nombre] = insumo
    return insumos


def crear_productos(insumos):
    recetas = {
        "Torta de chocolate": {
            "precio": "18990",
            "porciones": 12,
            "descripcion": "Bizcocho húmedo de chocolate con ganache y decoración personalizada.",
            "bom": [
                ("Harina sin polvos", "500"),
                ("Azúcar", "400"),
                ("Huevos", "8"),
                ("Chocolate cobertura", "350"),
                ("Mantequilla", "250"),
                ("Caja para torta", "1"),
            ],
        },
        "Cheesecake de frutilla": {
            "precio": "15990",
            "porciones": 10,
            "descripcion": "Base de galleta, crema de queso y cubierta de frutillas frescas.",
            "bom": [
                ("Harina sin polvos", "250"),
                ("Azúcar", "300"),
                ("Crema para batir", "500"),
                ("Frutillas", "600"),
                ("Mantequilla", "150"),
                ("Caja para torta", "1"),
            ],
        },
        "Torta de manjar": {
            "precio": "17990",
            "porciones": 12,
            "descripcion": "Bizcocho clásico relleno de manjar y crema chantilly.",
            "bom": [
                ("Harina sin polvos", "450"),
                ("Azúcar", "350"),
                ("Huevos", "7"),
                ("Manjar", "500"),
                ("Crema para batir", "400"),
                ("Caja para torta", "1"),
            ],
        },
    }

    productos = {}
    for nombre, datos in recetas.items():
        producto, _ = Producto.objects.get_or_create(
            nombre=nombre,
            defaults={
                "precio_base": Decimal(datos["precio"]),
                "porciones": datos["porciones"],
                "descripcion": datos["descripcion"],
            },
        )
        for insumo_nombre, cantidad in datos["bom"]:
            RecetaInsumo.objects.get_or_create(
                producto=producto,
                insumo=insumos[insumo_nombre],
                defaults={"cantidad": Decimal(cantidad)},
            )
        productos[nombre] = producto
    return productos


def crear_clientes():
    datos = [
        ("María Fernández", "+56912345678", "maria@correo.cl", "Av. Alemania 1234, Temuco"),
        ("Pedro Soto", "+56987654321", "pedro@correo.cl", "Los Aromos 456, Temuco"),
        ("Colegio San José", "+56911112222", "compras@sanjose.cl", "Prat 789, Temuco"),
        ("Camila Rojas", "+56933334444", "camila@correo.cl", "Av. Recabarren 321, Temuco"),
    ]
    clientes = []
    for nombre, telefono, email, direccion in datos:
        cliente, _ = Cliente.objects.get_or_create(
            nombre=nombre,
            defaults={"telefono": telefono, "email": email, "direccion": direccion},
        )
        clientes.append(cliente)
    return clientes


def crear_pedidos(clientes, productos):
    ahora = timezone.now()
    admin = User.objects.filter(username="admin").first()
    cocina = User.objects.filter(username="cocina").first()
    ventas = User.objects.filter(username="ventas").first()

    plantilla = [
        (clientes[0], "recibido", 3, "Torta de chocolate", 1, "Temática unicornio, tonos pastel."),
        (clientes[1], "preparacion", 2, "Cheesecake de frutilla", 2, "Decoración con frutillas naturales."),
        (clientes[2], "horneado", 1, "Torta de manjar", 3, "Logo del colegio en la superficie."),
        (clientes[3], "listo", 0, "Torta de chocolate", 1, "Dedicatoria 'Feliz cumpleaños, Ana'."),
    ]

    for cliente, estado, dias, producto, cantidad, diseno in plantilla:
        if Pedido.objects.filter(cliente=cliente, descripcion_diseno=diseno).exists():
            continue

        pedido = Pedido.objects.create(
            cliente=cliente,
            estado=estado,
            fecha_entrega=ahora + timedelta(days=dias, hours=2),
            descripcion_diseno=diseno,
            anticipo=Decimal("5000"),
            costo_despacho=Decimal("3000"),
            creado_por=ventas,
            insumos_descontados=False,
        )
        PedidoDetalle.objects.create(
            pedido=pedido, producto=productos[producto], cantidad=cantidad
        )
        HistorialEstado.objects.create(
            pedido=pedido,
            estado_anterior="",
            estado_nuevo="recibido",
            usuario=ventas,
            comentario="Pedido registrado en ventas.",
        )
        if estado != "recibido":
            HistorialEstado.objects.create(
                pedido=pedido,
                estado_anterior="recibido",
                estado_nuevo=estado,
                usuario=cocina if estado in ("preparacion", "horneado") else admin,
                comentario="Avance de producción.",
            )


def main():
    crear_usuarios()
    insumos = crear_insumos()
    productos = crear_productos(insumos)
    clientes = crear_clientes()
    crear_pedidos(clientes, productos)

    print("Datos de prueba cargados.")
    print(f"Usuarios: {', '.join(u for u, *_ in USUARIOS)} — clave: {CLAVE}")
    print(f"Insumos: {Insumo.objects.count()} | Productos: {Producto.objects.count()}")
    print(f"Clientes: {Cliente.objects.count()} | Pedidos: {Pedido.objects.count()}")


if __name__ == "__main__":
    main()
