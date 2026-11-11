"""Tienda pública: catálogo, carrito, checkout, seguimiento y cuenta."""

from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .. import carrito
from ..forms import (
    CheckoutForm,
    ClienteCuentaForm,
    RegistroClienteForm,
    SeguimientoForm,
)
from ..models import (
    CategoriaProducto,
    Cliente,
    Despacho,
    MensajeContacto,
    MovimientoInsumo,
    Pedido,
    PedidoDetalle,
    Perfil,
    Producto,
)
from django.db.models import Count, F, Q
from ..roles import ROLES_INTERNOS, puede, rol_de


def _cliente_para_checkout(request, form):
    """Reutiliza la ficha del usuario o crea/actualiza una ficha de invitado."""
    email = form.cleaned_data["email"].strip().lower()
    nombre = form.cleaned_data["nombre"].strip()
    telefono = form.cleaned_data["telefono"].strip()

    cliente = cliente_de(request.user)
    if cliente is None:
        cliente = Cliente.objects.filter(email__iexact=email).first()
    if cliente is None:
        cliente = Cliente(nombre=nombre, email=email, telefono=telefono)
    else:
        cliente.nombre = cliente.nombre or nombre
        cliente.email = cliente.email or email
        cliente.telefono = cliente.telefono or telefono
    if request.user.is_authenticated and cliente.user_id is None:
        cliente.user = request.user
    cliente.save()
    return cliente


def cliente_de(user):
    """Ficha de cliente vinculada al usuario, si existe."""
    if not user.is_authenticated:
        return None
    return Cliente.objects.filter(user=user).first()


def _validar_stock(lineas):
    problemas = []
    for linea in lineas:
        producto = linea["producto"]
        disponibles = producto.unidades_disponibles
        if disponibles is None:
            continue
        if disponibles <= 0:
            problemas.append(f"{producto.nombre} no tiene stock disponible hoy.")
        elif linea["cantidad"] > disponibles:
            problemas.append(
                f"{producto.nombre}: pediste {linea['cantidad']} y solo se pueden "
                f"producir {disponibles} con el stock actual."
            )
    if problemas:
        raise DjangoValidationError(problemas)


def _crear_pedido_web(request, form, lineas, costo_despacho):
    datos = form.cleaned_data
    cliente = _cliente_para_checkout(request, form)
    modalidad = datos["modalidad"]

    pedido = Pedido(
        cliente=cliente,
        canal="web",
        modalidad=modalidad,
        fecha_entrega=datos["fecha_entrega"],
        direccion_entrega=datos["direccion_entrega"]
        if modalidad == "despacho"
        else "",
        telefono_contacto=datos["telefono"],
        descripcion_diseno=datos["descripcion_diseno"],
        costo_despacho=costo_despacho
        if modalidad == "despacho"
        else Decimal("0"),
        creado_por=request.user if request.user.is_authenticated else None,
    )
    pedido.full_clean(exclude=["codigo", "token_seguimiento"])
    pedido.save()

    for linea in lineas:
        PedidoDetalle.objects.create(
            pedido=pedido,
            producto=linea["producto"],
            cantidad=linea["cantidad"],
            precio_unitario=linea["producto"].precio_base,
            personalizacion=linea["personalizacion"],
        )
    return pedido


def _puede_ver_contacto(request, pedido):
    """Datos personales solo para el dueño del pedido o el personal interno."""
    if not request.user.is_authenticated:
        return False
    return (
        rol_de(request.user) in ROLES_INTERNOS
        or pedido.cliente.user_id == request.user.id
    )


def tienda(request):
    categoria = request.GET.get("categoria", "").strip()
    productos = (
        Producto.objects.filter(activo=True)
        .select_related("categoria")
        .prefetch_related("ingredientes__insumo")
    )
    if categoria:
        productos = productos.filter(categoria__nombre__iexact=categoria)

    categorias = CategoriaProducto.objects.annotate(
        total=Count("productos", filter=Q(productos__activo=True))
    ).filter(total__gt=0)

    lineas, total, unidades = carrito.detalle(request)
    return render(
        request,
        "tienda.html",
        {
            "productos": productos,
            "categorias": categorias,
            "categoria_actual": categoria,
            "lineas": lineas,
            "carrito_total": total,
            "carrito_unidades": unidades,
        },
    )


def producto_detalle(request, pk):
    producto = get_object_or_404(
        Producto.objects.select_related("categoria").prefetch_related(
            "ingredientes__insumo"
        ),
        pk=pk,
        activo=True,
    )
    lineas, total, unidades = carrito.detalle(request)
    return render(
        request,
        "producto_detalle.html",
        {
            "producto": producto,
            "lineas": lineas,
            "carrito_total": total,
            "carrito_unidades": unidades,
        },
    )


def carrito_ver(request):
    lineas, total, unidades = carrito.detalle(request)
    return render(
        request,
        "carrito.html",
        {"lineas": lineas, "carrito_total": total, "carrito_unidades": unidades},
    )


@require_POST
def carrito_agregar(request, pk):
    producto = get_object_or_404(Producto, pk=pk, activo=True)
    cantidad = request.POST.get("cantidad", 1)
    try:
        cantidad = max(int(cantidad), 1)
    except (TypeError, ValueError):
        cantidad = 1
    carrito.agregar(
        request,
        producto,
        cantidad=cantidad,
        personalizacion=request.POST.get("personalizacion", "").strip(),
    )
    messages.success(request, f"Agregaste {producto.nombre} al carrito.")
    return redirect(request.POST.get("next") or "carrito")


@require_POST
def carrito_actualizar(request, pk):
    carrito.actualizar(request, pk, request.POST.get("cantidad", 1))
    return redirect("carrito")


@require_POST
def carrito_quitar(request, pk):
    carrito.quitar(request, pk)
    messages.info(request, "Producto quitado del carrito.")
    return redirect("carrito")


def checkout(request):
    lineas, total, unidades = carrito.detalle(request)
    if not lineas:
        messages.info(request, "Tu carrito está vacío.")
        return redirect("tienda")

    cliente = cliente_de(request.user)
    despacho = Decimal("3500")

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                _validar_stock(lineas)
                with transaction.atomic():
                    pedido = _crear_pedido_web(request, form, lineas, despacho)
            except DjangoValidationError as error:
                for mensaje in error.messages:
                    form.add_error(None, mensaje)
            else:
                carrito.vaciar(request)
                messages.success(
                    request,
                    f"¡Pedido {pedido.codigo} recibido! Te contactaremos para "
                    "coordinar el pago del anticipo.",
                )
                return redirect(
                    "seguimiento_detalle", token=pedido.token_seguimiento
                )
    else:
        initial = {
            "nombre": (cliente.nombre if cliente else request.user.get_full_name()),
            "telefono": cliente.telefono if cliente else "",
            "email": (cliente.email if cliente else request.user.email),
            "modalidad": "retiro",
            "direccion_entrega": cliente.direccion if cliente else "",
        }
        form = CheckoutForm(initial=initial)

    fecha_minima = timezone.localtime() + timedelta(
        hours=Pedido.LEAD_TIME_HORAS
    )
    form.fields["fecha_entrega"].widget.attrs["min"] = fecha_minima.strftime(
        "%Y-%m-%dT%H:%M"
    )

    return render(
        request,
        "checkout.html",
        {
            "form": form,
            "lineas": lineas,
            "carrito_total": total,
            "carrito_unidades": unidades,
            "costo_despacho": despacho,
            "total_con_despacho": total + despacho,
            "fecha_minima": fecha_minima,
        },
    )


def registro(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = RegistroClienteForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            with transaction.atomic():
                user = User.objects.create_user(
                    username=datos["username"],
                    email=datos["email"],
                    password=datos["password1"],
                    first_name=datos["nombre"],
                    last_name=datos["apellido"],
                )
                Perfil.objects.create(
                    user=user, rol="cliente", telefono=datos["telefono"]
                )
                Cliente.objects.create(
                    user=user,
                    nombre=f"{datos['nombre']} {datos['apellido']}".strip(),
                    telefono=datos["telefono"],
                    email=datos["email"],
                )
            login(request, user)
            messages.success(
                request, "¡Cuenta creada! Ya puedes hacer tu pedido."
            )
            return redirect("tienda")
    else:
        form = RegistroClienteForm()

    return render(request, "registro.html", {"form": form})


def seguimiento(request):
    form = SeguimientoForm(request.GET or None)
    pedido = None
    if request.GET.get("codigo"):
        if form.is_valid():
            valor = form.cleaned_data["codigo"].strip()
            pedido = (
                Pedido.objects.select_related("cliente", "confirmado_por")
                .prefetch_related(
                    "detalles__producto", "historial__usuario", "pagos", "despacho"
                )
                .filter(Q(codigo__iexact=valor) | Q(token_seguimiento=valor))
                .first()
            )
            if pedido is None:
                form.add_error("codigo", "No encontramos un pedido con ese código.")
    return render(
        request,
        "seguimiento.html",
        {
            "form": form,
            "pedido": pedido,
            "mostrar_contacto": pedido is not None
            and _puede_ver_contacto(request, pedido),
        },
    )


def seguimiento_detalle(request, token):
    pedido = get_object_or_404(
        Pedido.objects.select_related("cliente", "confirmado_por").prefetch_related(
            "detalles__producto", "historial__usuario", "pagos", "despacho"
        ),
        token_seguimiento=token,
    )
    return render(
        request,
        "seguimiento.html",
        {
            "form": SeguimientoForm(),
            "pedido": pedido,
            "publico": True,
            "mostrar_contacto": _puede_ver_contacto(request, pedido),
        },
    )


@login_required
def mis_pedidos(request):
    if rol_de(request.user) in ROLES_INTERNOS:
        return redirect("pedidos")
    pedidos = (
        Pedido.objects.filter(cliente__user=request.user)
        .select_related("cliente")
        .order_by("-fecha_pedido")
    )
    return render(request, "mis_pedidos.html", {"pedidos": pedidos})


def quienes_somos(request):
    return render(request, "quienes_somos.html")


def servicios(request):
    return render(
        request,
        "servicios.html",
        {"productos": Producto.objects.filter(activo=True)[:6]},
    )


def contacto(request):
    if request.method == "POST":
        MensajeContacto.objects.create(
            nombre=request.POST.get("nombre", ""),
            email=request.POST.get("email", ""),
            telefono=request.POST.get("telefono", ""),
            mensaje=request.POST.get("mensaje", ""),
        )
        messages.success(
            request,
            "¡Gracias por escribirnos! Te responderemos a la brevedad.",
        )
        return redirect("contacto")
    return render(request, "contacto.html")


def home(request):
    """Landing pública para visitantes y panel distinto según el rol."""
    if not request.user.is_authenticated:
        return render(
            request,
            "landing.html",
            {
                "productos": Producto.objects.filter(activo=True)
                .select_related("categoria")
                .prefetch_related("ingredientes__insumo")[:6],
                "categorias": CategoriaProducto.objects.all(),
            },
        )

    if rol_de(request.user) == "cliente":
        return redirect("tienda")

    hoy = timezone.localdate()
    pedidos = Pedido.objects.select_related("cliente")
    activos = pedidos.exclude(estado__in=["entregado", "cancelado"])

    contexto = {
        "hoy": hoy,
        "total_pedidos": pedidos.count(),
        "pendientes": activos.count(),
        "stock_bajo": Insumo.objects.filter(
            stock_actual__lte=F("stock_minimo")
        ).count(),
        "insumos_bajo": [
            insumo
            for insumo in Insumo.objects.select_related("categoria")
            if insumo.stock_bajo
        ],
    }

    rol = rol_de(request.user)
    if rol == "admin":
        contexto.update(
            {
                "proximos": activos.order_by("fecha_entrega")[:6],
                "ventas_total": sum(
                    (p.total for p in pedidos.exclude(estado="cancelado")),
                    start=0,
                ),
                "pedidos_hoy": pedidos.filter(fecha_pedido__date=hoy).count(),
                "nuevos_web": pedidos.filter(
                    canal="web", estado="recibido"
                ).count(),
                "equipo_total": Perfil.objects.exclude(rol="cliente").count(),
                "clientes_total": Cliente.objects.count(),
                "ultimos_movimientos": MovimientoInsumo.objects.select_related(
                    "insumo"
                )[:5],
                "por_estado": [
                    (etiqueta, pedidos.filter(estado=clave).count())
                    for clave, etiqueta in Pedido.ESTADOS
                ],
            }
        )
    elif rol == "ventas":
        contexto.update(
            {
                "mis_pedidos": pedidos.filter(creado_por=request.user)[:8],
                "proximos": activos.order_by("fecha_entrega")[:6],
                "ventas_mes": sum(
                    (
                        p.total
                        for p in pedidos.filter(
                            fecha_pedido__year=hoy.year,
                            fecha_pedido__month=hoy.month,
                        ).exclude(estado="cancelado")
                    ),
                    start=0,
                ),
                "clientes_total": Cliente.objects.count(),
                "productos_total": Producto.objects.filter(activo=True).count(),
                "por_confirmar": pedidos.filter(estado="recibido").count(),
            }
        )
    elif rol == "cocina":
        contexto.update(
            {
                "en_preparacion": activos.filter(estado="preparacion").order_by(
                    "fecha_entrega"
                ),
                "en_horneado": activos.filter(estado="horneado").order_by(
                    "fecha_entrega"
                ),
                "por_estado": [
                    (etiqueta, pedidos.filter(estado=clave).count())
                    for clave, etiqueta in Pedido.ESTADOS
                    if clave in ("preparacion", "horneado", "calidad", "listo")
                ],
            }
        )
    elif rol == "calidad":
        contexto.update(
            {
                "en_calidad": activos.filter(estado="calidad").order_by(
                    "fecha_entrega"
                ),
                "listos": pedidos.filter(estado="listo").order_by(
                    "fecha_entrega"
                ),
            }
        )
    elif rol == "despacho":
        contexto.update(
            {
                "listos": pedidos.filter(
                    estado="listo", modalidad="despacho"
                ).order_by("fecha_entrega"),
                "despachos_pendientes": Despacho.objects.select_related(
                    "pedido", "repartidor"
                ).filter(fecha_entrega__isnull=True),
                "entregas_hoy": Despacho.objects.filter(
                    fecha_entrega__date=hoy
                ).select_related("pedido"),
            }
        )

    return render(request, "home.html", contexto)
