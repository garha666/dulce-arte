"""
Datos de prueba para Dulce Arte.
Uso:  python seed_data.py

Crea usuarios por rol, insumos, catálogo con recetas, clientes (uno con cuenta),
y pedidos que recorren el flujo real (pago → confirmado → producción → entrega).
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
    CategoriaProducto,
    Cliente,
    Despacho,
    Insumo,
    Pago,
    Pedido,
    PedidoDetalle,
    Perfil,
    Producto,
    RecetaInsumo,
)

CLAVE = "Dulce2026!"
CLAVE_CLIENTE = "Cliente2026!"

USUARIOS = [
    (
        "admin",
        "Administrador",
        "Dulce Arte",
        "admin",
        "completo",
        "Dirección y gestión",
        "",
        "",
        "Acceso total al panel, Admin y API.",
    ),
    (
        "ventas",
        "Vendedor",
        "Mostrador",
        "ventas",
        "manana",
        "Mostrador y cotizaciones",
        "",
        "",
        "Atiende pedidos web, teléfono y pagos.",
    ),
    (
        "cocina",
        "Jefa",
        "de Cocina",
        "cocina",
        "manana",
        "Repostería y decoración",
        "",
        "",
        "Responsable de producción y BOM.",
    ),
    (
        "calidad",
        "Control",
        "de Calidad",
        "calidad",
        "tarde",
        "Inocuidad y terminación",
        "",
        "",
        "Aprueba el paso a Listo.",
    ),
    (
        "despacho",
        "Repartidor",
        "Zona Centro",
        "despacho",
        "tarde",
        "Reparto y entregas",
        "Temuco centro",
        "Furgón",
        "Confirma entregas con evidencia.",
    ),
]

CATEGORIAS_PRODUCTO = {
    "Tortas": "Tortas completas para cumpleaños y celebraciones.",
    "Postres": "Cheesecakes, cupcakes y piezas individuales.",
    "Mesas dulces": "Surtidos para eventos y reuniones.",
}


def crear_usuarios():
    for username, nombre, apellido, rol, turno, especialidad, zona, vehiculo, notas in USUARIOS:
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
        perfil, _ = Perfil.objects.get_or_create(user=user, defaults={"rol": rol})
        perfil.rol = rol
        perfil.turno = perfil.turno or turno
        perfil.especialidad = perfil.especialidad or especialidad
        perfil.zona = perfil.zona or zona
        perfil.vehiculo = perfil.vehiculo or vehiculo
        perfil.notas = perfil.notas or notas
        perfil.save()


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
    categorias = {
        nombre: CategoriaProducto.objects.get_or_create(
            nombre=nombre, defaults={"descripcion": descripcion}
        )[0]
        for nombre, descripcion in CATEGORIAS_PRODUCTO.items()
    }

    recetas = {
        "Torta de chocolate": {
            "precio": "18990",
            "porciones": 12,
            "categoria": "Tortas",
            "imagen": "productos/chocolate.jpg",
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
            "categoria": "Postres",
            "imagen": "productos/cheesecake.jpg",
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
            "categoria": "Tortas",
            "imagen": "productos/manjar.jpg",
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
        "Torta de zanahoria": {
            "precio": "14990",
            "porciones": 10,
            "categoria": "Tortas",
            "imagen": "productos/zanahoria.jpg",
            "descripcion": "Bizcocho especiado de zanahoria con frosting de queso crema.",
            "bom": [
                ("Harina sin polvos", "400"),
                ("Azúcar", "300"),
                ("Huevos", "6"),
                ("Mantequilla", "200"),
                ("Caja para torta", "1"),
            ],
        },
        "Caja de cupcakes": {
            "precio": "12990",
            "porciones": 12,
            "categoria": "Mesas dulces",
            "imagen": "productos/cupcakes.jpg",
            "descripcion": "Doce cupcakes surtidos con buttercream y decoración temática.",
            "bom": [
                ("Harina sin polvos", "300"),
                ("Azúcar", "250"),
                ("Huevos", "5"),
                ("Mantequilla", "200"),
                ("Crema para batir", "300"),
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
                "categoria": categorias[datos["categoria"]],
                "imagen_estatica": datos["imagen"],
            },
        )
        if producto.categoria_id is None:
            producto.categoria = categorias[datos["categoria"]]
            producto.save(update_fields=["categoria"])
        if not producto.imagen_estatica:
            producto.imagen_estatica = datos["imagen"]
            producto.save(update_fields=["imagen_estatica"])
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


def crear_cuenta_cliente(clientes):
    """Vincula a María con una cuenta real de la tienda."""
    user, creado = User.objects.get_or_create(
        username="cliente",
        defaults={
            "first_name": "María",
            "last_name": "Fernández",
            "email": "maria@correo.cl",
        },
    )
    if creado:
        user.set_password(CLAVE_CLIENTE)
        user.save()
    Perfil.objects.get_or_create(
        user=user, defaults={"rol": "cliente", "telefono": "+56912345678"}
    )

    cliente = clientes[0]
    if cliente.user_id is None:
        cliente.user = user
        cliente.save(update_fields=["user"])
    return cliente


def _crear_pago(pedido, monto, metodo="transferencia", tipo="anticipo"):
    Pago.objects.get_or_create(
        pedido=pedido,
        monto=Decimal(monto),
        defaults={"metodo": metodo, "tipo": tipo, "referencia": "Seed"},
    )


def crear_pedidos(clientes, productos):
    ahora = timezone.now()
    admin = User.objects.get(username="admin")
    cocina = User.objects.get(username="cocina")
    ventas = User.objects.get(username="ventas")
    despacho_user = User.objects.get(username="despacho")

    # (cliente, estado objetivo, días, modalidad, producto, cantidad, diseño, pago)
    plantilla = [
        (clientes[0], "recibido", 3, "retiro", "Torta de chocolate", 1,
         "Temática unicornio, tonos pastel.", "0"),
        (clientes[1], "preparacion", 2, "despacho", "Cheesecake de frutilla", 2,
         "Decoración con frutillas naturales.", "5000"),
        (clientes[2], "horneado", 1, "despacho", "Torta de manjar", 3,
         "Logo del colegio en la superficie.", "10000"),
        (clientes[3], "listo", 1, "despacho", "Torta de chocolate", 1,
         "Dedicatoria 'Feliz cumpleaños, Ana'.", "18990"),
        (clientes[0], "entregado", -5, "retiro", "Torta de zanahoria", 1,
         "Entrega pasada para historial.", "14990"),
    ]

    ruta = ["confirmado", "preparacion", "horneado", "calidad", "listo", "entregado"]

    for cliente, objetivo, dias, modalidad, producto, cantidad, diseno, pago in plantilla:
        if Pedido.objects.filter(cliente=cliente, descripcion_diseno=diseno).exists():
            continue

        pedido = Pedido.objects.create(
            cliente=cliente,
            canal="web" if cliente.user_id else "mostrador",
            modalidad=modalidad,
            fecha_entrega=ahora + timedelta(days=dias, hours=2),
            direccion_entrega=cliente.direccion if modalidad == "despacho" else "",
            telefono_contacto=cliente.telefono,
            descripcion_diseno=diseno,
            costo_despacho=Decimal("3500") if modalidad == "despacho" else Decimal("0"),
            creado_por=ventas,
        )
        PedidoDetalle.objects.create(
            pedido=pedido, producto=productos[producto], cantidad=cantidad
        )

        if Decimal(pago) > 0:
            _crear_pago(
                pedido,
                pago,
                tipo="completo" if Decimal(pago) >= pedido.total else "anticipo",
            )

        if objetivo != "recibido":
            # Recorre el flujo real para que historial, stock y fechas sean coherentes.
            for estado in ruta:
                if estado == "entregado" and modalidad == "despacho":
                    Despacho.objects.get_or_create(
                        pedido=pedido,
                        defaults={
                            "direccion": pedido.direccion_entrega,
                            "repartidor": despacho_user,
                            "fecha_salida": ahora - timedelta(days=abs(dias) + 1),
                        },
                    )
                if estado == "entregado" and modalidad == "retiro":
                    pedido.retirado_por = cliente.nombre
                    pedido.save(update_fields=["retirado_por"])
                usuario = cocina if estado in ("preparacion", "horneado") else admin
                pedido.cambiar_estado(estado, usuario=usuario, comentario="Seed")
                if estado == objetivo:
                    break

        # Un pedido queda en reparto para mostrar el tablero de despachos.
        if objetivo == "listo" and modalidad == "despacho":
            Despacho.objects.get_or_create(
                pedido=pedido,
                defaults={
                    "direccion": pedido.direccion_entrega,
                    "repartidor": despacho_user,
                },
            )


def main():
    crear_usuarios()
    insumos = crear_insumos()
    productos = crear_productos(insumos)
    clientes = crear_clientes()
    crear_cuenta_cliente(clientes)
    crear_pedidos(clientes, productos)

    print("Datos de prueba cargados.")
    print(f"Usuarios internos: {', '.join(u for u, *_ in USUARIOS)} — clave: {CLAVE}")
    print(f"Cliente demo: cliente — clave: {CLAVE_CLIENTE}")
    print(f"Insumos: {Insumo.objects.count()} | Productos: {Producto.objects.count()}")
    print(f"Clientes: {Cliente.objects.count()} | Pedidos: {Pedido.objects.count()}")


if __name__ == "__main__":
    main()
