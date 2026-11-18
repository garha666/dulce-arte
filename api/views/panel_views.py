"""Panel interno: pedidos, equipo, kanban, inventario y despachos."""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..forms import (
    ClienteCuentaForm,
    ConfirmarEntregaForm,
    DespachoForm,
    EstadoForm,
    InsumoForm,
    PagoForm,
    PedidoDetalleFormSet,
    PedidoEdicionForm,
    PedidoInternoForm,
    UsuarioInternoForm,
)
from ..models import (
    Cliente,
    Despacho,
    Insumo,
    Pedido,
    PedidoDetalle,
    Perfil,
    Producto,
)
from ..roles import (
    ROLES_EQUIPO,
    ROLES_INFO,
    ROLES_INTERNOS,
    ROLES_PEDIDOS,
    puede,
    rol_de,
    rol_requerido,
)
from ..services.despacho import crear_despacho


# --------------------------------------------------------------------------- #
#  Utilidades internas
# --------------------------------------------------------------------------- #


def _detalle_queryset():
    return Pedido.objects.select_related("cliente", "confirmado_por").prefetch_related(
        "detalles__producto", "historial__usuario", "pagos", "despacho"
    )


# =========================================================================== #
#  Panel interno: pedidos
# =========================================================================== #


@login_required
def pedidos_page(request):
    if rol_de(request.user) not in ROLES_INTERNOS:
        messages.error(request, "Tu rol no tiene acceso a esa sección.")
        return redirect("home")

    pedidos = Pedido.objects.select_related("cliente").order_by("-fecha_pedido")
    estado = request.GET.get("estado", "")
    busqueda = request.GET.get("q", "").strip()
    if estado:
        pedidos = pedidos.filter(estado=estado)
    if busqueda:
        pedidos = pedidos.filter(
            Q(codigo__icontains=busqueda)
            | Q(cliente__nombre__icontains=busqueda)
            | Q(cliente__telefono__icontains=busqueda)
        )

    return render(
        request,
        "pedidos.html",
        {
            "pedidos": pedidos[:200],
            "estados": Pedido.ESTADOS,
            "estado_actual": estado,
            "busqueda": busqueda,
            "puede_crear": puede(request.user, "admin", "ventas"),
            "form": PedidoInternoForm(),
        },
    )


@rol_requerido("admin", "ventas")
@require_POST
def pedido_crear(request):
    form = PedidoInternoForm(request.POST)
    if not form.is_valid():
        for errores in form.errors.values():
            for error in errores:
                messages.error(request, error)
        return redirect("pedidos")

    try:
        with transaction.atomic():
            pedido = form.save(commit=False)
            pedido.creado_por = request.user
            pedido.full_clean(exclude=["codigo", "token_seguimiento"])
            pedido.save()
            PedidoDetalle.objects.create(
                pedido=pedido,
                producto=form.cleaned_data["producto"],
                cantidad=form.cleaned_data["cantidad"],
                personalizacion=form.cleaned_data["personalizacion"],
            )
    except DjangoValidationError as error:
        for mensaje in error.messages:
            messages.error(request, mensaje)
        return redirect("pedidos")

    messages.success(request, f"Pedido {pedido.codigo} registrado correctamente.")
    return redirect("pedido_detalle", pk=pedido.pk)


@login_required
def pedido_detalle_page(request, pk):
    pedido = get_object_or_404(_detalle_queryset(), pk=pk)

    es_interno = rol_de(request.user) in ROLES_INTERNOS
    es_dueno = pedido.cliente.user_id == request.user.id
    if not es_interno and not es_dueno:
        messages.error(request, "No tienes acceso a ese pedido.")
        return redirect(
            "mis_pedidos" if rol_de(request.user) == "cliente" else "home"
        )

    rol = rol_de(request.user)
    transiciones = pedido.transiciones_para(rol)
    cerrar_retiro = (
        pedido.estado == "listo"
        and pedido.modalidad == "retiro"
        and rol in ("admin", "ventas", "despacho")
    )
    if cerrar_retiro:
        transiciones = [
            transicion for transicion in transiciones if transicion[0] != "entregado"
        ]
    pedido.transiciones_visibles = transiciones
    return render(
        request,
        "pedido_detalle.html",
        {
            "pedido": pedido,
            "es_interno": es_interno,
            "cerrar_retiro": cerrar_retiro,
            "puede_editar": rol in ROLES_PEDIDOS and not pedido.insumos_descontados,
            "puede_crear_pago": puede(request.user, "admin", "ventas"),
            "pago_form": PagoForm(initial={"tipo": "anticipo"}),
            "estado_form": EstadoForm(),
        },
    )


@rol_requerido("admin", "ventas")
def pedido_editar(request, pk):
    """Edita la cabecera y los productos de un pedido antes del descuento de BOM."""
    pedido = get_object_or_404(
        Pedido.objects.select_related("cliente").prefetch_related(
            "detalles__producto"
        ),
        pk=pk,
    )
    if pedido.insumos_descontados:
        messages.error(
            request,
            "Este pedido ya descontó insumos: no se puede editar para no romper "
            "la trazabilidad del inventario.",
        )
        return redirect("pedido_detalle", pk=pedido.pk)

    if request.method == "POST":
        form = PedidoEdicionForm(request.POST, instance=pedido)
        formset = PedidoDetalleFormSet(request.POST, instance=pedido)
        if form.is_valid() and formset.is_valid():
            vigentes = [
                detalle
                for detalle in formset.forms
                if detalle.cleaned_data
                and not detalle.cleaned_data.get("DELETE")
                and detalle.cleaned_data.get("producto")
            ]
            if not vigentes:
                form.add_error(None, "El pedido debe conservar al menos un producto.")
            else:
                with transaction.atomic():
                    form.save()
                    formset.save()
                messages.success(
                    request, f"Pedido {pedido.codigo} actualizado correctamente."
                )
                return redirect("pedido_detalle", pk=pedido.pk)
    else:
        form = PedidoEdicionForm(instance=pedido)
        formset = PedidoDetalleFormSet(instance=pedido)

    fecha_minima = timezone.localtime() + timedelta(hours=Pedido.LEAD_TIME_HORAS)
    form.fields["fecha_entrega"].widget.attrs["min"] = fecha_minima.strftime(
        "%Y-%m-%dT%H:%M"
    )
    return render(
        request,
        "pedido_editar.html",
        {
            "pedido": pedido,
            "form": form,
            "formset": formset,
            "fecha_minima": fecha_minima,
        },
    )


@rol_requerido("admin", "ventas", "cocina", "calidad", "despacho")
@require_POST
def pedido_cambiar_estado(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    nuevo_estado = request.POST.get("estado", "")
    comentario = request.POST.get("comentario", "").strip()
    try:
        pedido.cambiar_estado(
            nuevo_estado, usuario=request.user, comentario=comentario
        )
    except DjangoValidationError as error:
        for mensaje in error.messages:
            messages.error(request, mensaje)
    else:
        messages.success(
            request,
            f"{pedido.codigo} pasó a {pedido.get_estado_display()}.",
        )
    return redirect(request.POST.get("next") or f"/pedidos/{pedido.pk}/")


@rol_requerido("admin", "ventas")
@require_POST
def pedido_registrar_pago(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    form = PagoForm(request.POST)
    if not form.is_valid():
        for errores in form.errors.values():
            for error in errores:
                messages.error(request, error)
    else:
        pago = form.save(commit=False)
        pago.pedido = pedido
        pago.registrado_por = request.user
        pago.full_clean()
        pago.save()
        messages.success(
            request,
            f"Pago de ${pago.monto} registrado. Estado: {pedido.estado_pago_display}.",
        )
    return redirect("pedido_detalle", pk=pedido.pk)


# =========================================================================== #
#  Panel interno: equipo, clientes y guía de roles
# =========================================================================== #


@rol_requerido(*ROLES_EQUIPO)
def equipo_page(request):
    equipo = (
        Perfil.objects.select_related("user")
        .exclude(rol="cliente")
        .order_by("rol", "user__first_name", "user__username")
    )
    return render(
        request,
        "equipo.html",
        {
            "equipo": equipo,
            "roles_info": ROLES_INFO,
            "form_usuario": UsuarioInternoForm(),
            "form_cliente": ClienteCuentaForm(),
            "clientes": Cliente.objects.select_related("user")
            .order_by("-creado")[:25],
        },
    )


@rol_requerido(*ROLES_EQUIPO)
@require_POST
def equipo_crear_usuario(request):
    form = UsuarioInternoForm(request.POST)
    if not form.is_valid():
        for errores in form.errors.values():
            for error in errores:
                messages.error(request, error)
        return redirect("equipo")

    datos = form.cleaned_data
    with transaction.atomic():
        user = User.objects.create_user(
            username=datos["username"],
            email=datos["email"],
            password=datos["password1"],
            first_name=datos["nombre"],
            last_name=datos["apellido"],
            is_staff=datos["rol"] == "admin",
            is_superuser=datos["rol"] == "admin",
        )
        Perfil.objects.create(
            user=user,
            rol=datos["rol"],
            telefono=datos["telefono"],
            turno=datos["turno"],
            especialidad=datos["especialidad"],
            zona=datos["zona"],
            vehiculo=datos["vehiculo"],
            notas=datos["notas"],
        )

    messages.success(
        request,
        f"Usuario {datos['username']} creado con rol "
        f"{dict(Perfil.ROLES)[datos['rol']]}.",
    )
    return redirect("equipo")


@rol_requerido(*ROLES_EQUIPO)
@require_POST
def equipo_crear_cliente(request):
    form = ClienteCuentaForm(request.POST)
    if not form.is_valid():
        for errores in form.errors.values():
            for error in errores:
                messages.error(request, error)
        return redirect("equipo")

    with transaction.atomic():
        cliente = form.save()
        username = (form.cleaned_data.get("username") or "").strip()
        if username:
            nombre = cliente.nombre.split(" ", 1)
            user = User.objects.create_user(
                username=username,
                email=cliente.email,
                password=form.cleaned_data["password1"],
                first_name=nombre[0],
                last_name=nombre[1] if len(nombre) > 1 else "",
            )
            Perfil.objects.create(
                user=user, rol="cliente", telefono=cliente.telefono
            )
            cliente.user = user
            cliente.save(update_fields=["user"])

    if cliente.user_id:
        messages.success(
            request,
            f"Cliente {cliente.nombre} creado con cuenta de tienda ({username}).",
        )
    else:
        messages.success(request, f"Ficha de cliente {cliente.nombre} creada.")
    return redirect("equipo")


# =========================================================================== #
#  Panel interno: producción, inventario y despachos
# =========================================================================== #


@rol_requerido("admin", "cocina", "calidad")
def kanban_page(request):
    rol = rol_de(request.user)
    columnas = []
    for clave, etiqueta in Pedido.ESTADOS:
        if clave in ("despachado", "cancelado"):
            continue
        pedidos_columna = list(
            Pedido.objects.filter(estado=clave)
            .select_related("cliente")
            .order_by("fecha_entrega")
        )
        for pedido in pedidos_columna:
            pedido.transiciones_visibles = pedido.transiciones_para(rol)
        columnas.append(
            {
                "clave": clave,
                "etiqueta": etiqueta,
                "pedidos": pedidos_columna,
            }
        )
    return render(request, "kanban.html", {"columnas": columnas})


@rol_requerido("admin", "cocina", "calidad")
def inventario_page(request):
    return render(
        request,
        "inventario.html",
        {
            "insumos": Insumo.objects.select_related("categoria").order_by(
                "nombre"
            ),
            "productos": Producto.objects.prefetch_related(
                "ingredientes__insumo"
            ),
            "puede_editar_insumos": puede(request.user, "admin", "cocina"),
            "puede_eliminar_insumos": puede(request.user, "admin"),
        },
    )


@rol_requerido("admin", "cocina")
def insumo_crear(request):
    if request.method == "POST":
        form = InsumoForm(request.POST)
        if form.is_valid():
            insumo = form.save()
            messages.success(request, f"Insumo «{insumo.nombre}» creado.")
            return redirect("inventario")
    else:
        form = InsumoForm()

    return render(
        request,
        "inventario_form.html",
        {"form": form, "titulo": "Nuevo insumo", "insumo": None},
    )


@rol_requerido("admin", "cocina")
def insumo_editar(request, pk):
    insumo = get_object_or_404(Insumo, pk=pk)

    if request.method == "POST":
        form = InsumoForm(request.POST, instance=insumo)
        if form.is_valid():
            form.save()
            messages.success(request, f"Insumo «{insumo.nombre}» actualizado.")
            return redirect("inventario")
    else:
        form = InsumoForm(instance=insumo)

    return render(
        request,
        "inventario_form.html",
        {"form": form, "titulo": f"Editar {insumo.nombre}", "insumo": insumo},
    )


@rol_requerido("admin")
@require_POST
def insumo_eliminar(request, pk):
    insumo = get_object_or_404(Insumo, pk=pk)

    if insumo.usos.exists():
        messages.error(
            request,
            f"No se puede eliminar {insumo.nombre}: se usa en una receta. "
            "Quítalo del BOM antes de borrarlo.",
        )
        return redirect("inventario")

    if insumo.movimientos.exists():
        messages.error(
            request,
            f"No se puede eliminar {insumo.nombre}: tiene movimientos de "
            "inventario y borrarlos rompería la auditoría.",
        )
        return redirect("inventario")

    nombre = insumo.nombre
    insumo.delete()
    messages.success(request, f"Insumo «{nombre}» eliminado.")
    return redirect("inventario")


@rol_requerido("admin", "despacho")
def despachos_page(request):
    return render(
        request,
        "despachos.html",
        {
            "despachos": Despacho.objects.select_related(
                "pedido__cliente", "repartidor"
            ).order_by("-fecha_salida"),
            "form": DespachoForm(),
            "confirmar_form": ConfirmarEntregaForm(),
            "retiros": Pedido.objects.filter(
                estado="listo", modalidad="retiro"
            ).select_related("cliente"),
        },
    )


@rol_requerido("admin", "despacho")
@require_POST
def despacho_crear(request):
    """Asigna el reparto y deja el pedido en estado Despachado."""
    form = DespachoForm(request.POST)
    if not form.is_valid():
        for errores in form.errors.values():
            for error in errores:
                messages.error(request, error)
        return redirect("despachos")

    try:
        despacho = crear_despacho(request, form)
    except DjangoValidationError as error:
        for mensaje in error.messages:
            messages.error(request, mensaje)
    else:
        messages.success(
            request,
            f"Despacho creado para {despacho.pedido.codigo}; el pedido salió a reparto.",
        )
    return redirect("despachos")


@rol_requerido("admin", "despacho")
@require_POST
def despacho_confirmar(request, pk):
    """Confirma la entrega con firma o comprobante y cierra el pedido."""
    despacho = get_object_or_404(
        Despacho.objects.select_related("pedido"), pk=pk
    )
    form = ConfirmarEntregaForm(request.POST, request.FILES)
    if not form.is_valid():
        for errores in form.errors.values():
            for error in errores:
                messages.error(request, error)
        return redirect("despachos")

    despacho.receptor_nombre = form.cleaned_data["receptor_nombre"]
    despacho.observaciones = form.cleaned_data["observaciones"]
    despacho.firma = form.cleaned_data["firma"]
    despacho.comprobante = form.cleaned_data["comprobante"]
    despacho.fecha_entrega = timezone.now()
    despacho.confirmado_por = request.user

    try:
        with transaction.atomic():
            despacho.full_clean()
            despacho.save()
            despacho.pedido.cambiar_estado(
                "entregado",
                usuario=request.user,
                comentario=f"Entrega confirmada del despacho {despacho.pk}.",
            )
    except DjangoValidationError as error:
        for mensaje in error.messages:
            messages.error(request, mensaje)
    else:
        messages.success(
            request,
            f"Entrega del pedido {despacho.pedido.codigo} confirmada correctamente.",
        )
    return redirect("despachos")


def _destino_retiro(request, pedido):
    """Vuelve a la pantalla desde donde se cerró el retiro."""
    destino = request.POST.get("next", "")
    if destino == "detalle":
        return redirect("pedido_detalle", pk=pedido.pk)
    if destino == "pedidos":
        return redirect("pedidos")
    return redirect("despachos")


@rol_requerido("admin", "ventas", "despacho")
@require_POST
def retiro_confirmar(request, pk):
    """Cierra un pedido de retiro indicando quién lo retiró."""
    pedido = get_object_or_404(Pedido, pk=pk)
    retirado_por = request.POST.get("retirado_por", "").strip()
    if not retirado_por:
        messages.error(request, "Indica quién retira el pedido.")
        return _destino_retiro(request, pedido)

    pedido.retirado_por = retirado_por
    pedido.save(update_fields=["retirado_por"])
    try:
        pedido.cambiar_estado(
            "entregado",
            usuario=request.user,
            comentario=f"Retirado en tienda por {retirado_por}.",
        )
    except DjangoValidationError as error:
        for mensaje in error.messages:
            messages.error(request, mensaje)
    else:
        messages.success(
            request,
            f"Pedido {pedido.codigo} vendido y entregado en tienda.",
        )
    return _destino_retiro(request, pedido)
