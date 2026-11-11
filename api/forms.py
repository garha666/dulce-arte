"""Formularios de la tienda y del panel interno.

Toda la validación de negocio vive en los modelos; los formularios solo
recogen los datos y delegan en `full_clean`.
"""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.forms import inlineformset_factory

from .models import Cliente, Despacho, Pago, Pedido, PedidoDetalle, Perfil, Producto

DATE_INPUT = forms.DateTimeInput(
    attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
)


class RegistroClienteForm(forms.Form):
    """Crea la cuenta de un cliente de la tienda."""

    nombre = forms.CharField(max_length=60, label="Nombre")
    apellido = forms.CharField(max_length=60, label="Apellido")
    username = forms.CharField(max_length=30, label="Usuario")
    email = forms.EmailField(label="Correo")
    telefono = forms.CharField(max_length=20, label="Teléfono")
    password1 = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Repetir contraseña")

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Ese usuario ya está en uso.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con ese correo.")
        return email

    def clean(self):
        datos = super().clean()
        if datos.get("password1") and datos.get("password1") != datos.get("password2"):
            self.add_error("password2", "Las contraseñas no coinciden.")
        return datos


class CheckoutForm(forms.Form):
    """Datos de contacto, entrega y pago elegidos en la tienda."""

    nombre = forms.CharField(max_length=120, label="Nombre de quien recibe")
    telefono = forms.CharField(max_length=20, label="Teléfono")
    email = forms.EmailField(label="Correo")
    modalidad = forms.ChoiceField(
        choices=Pedido.MODALIDADES, initial="retiro", label="Entrega"
    )
    direccion_entrega = forms.CharField(
        max_length=200, required=False, label="Dirección de despacho"
    )
    fecha_entrega = forms.DateTimeField(widget=DATE_INPUT, label="Fecha y hora")
    descripcion_diseno = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Personalización (opcional)",
    )
    metodo_pago = forms.ChoiceField(
        choices=Pago.METODOS,
        initial="transferencia",
        label="Forma de pago",
    )
    acepta_terminos = forms.BooleanField(
        label="Acepto las condiciones del pedido y el plazo de 48 horas."
    )

    def clean(self):
        datos = super().clean()
        modalidad = datos.get("modalidad")
        direccion = (datos.get("direccion_entrega") or "").strip()
        if modalidad == "despacho" and not direccion:
            self.add_error(
                "direccion_entrega", "Indica la dirección para el despacho."
            )
        if modalidad == "retiro":
            datos["direccion_entrega"] = ""
        return datos


class PedidoInternoForm(forms.ModelForm):
    """Alta de pedido desde ventas/mostrador, con un producto por vez."""

    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(activo=True), label="Producto"
    )
    cantidad = forms.IntegerField(min_value=1, initial=1, label="Cantidad")
    personalizacion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        label="Personalización",
    )

    class Meta:
        model = Pedido
        fields = (
            "cliente",
            "canal",
            "modalidad",
            "fecha_entrega",
            "direccion_entrega",
            "telefono_contacto",
            "descripcion_diseno",
            "costo_despacho",
            "observaciones",
        )
        widgets = {
            "fecha_entrega": DATE_INPUT,
            "descripcion_diseno": forms.Textarea(attrs={"rows": 3}),
            "observaciones": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha_entrega"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["cliente"].queryset = self.fields["cliente"].queryset.order_by(
            "nombre"
        )


class EstadoForm(forms.Form):
    """Botón de transición del tablero Kanban."""

    estado = forms.CharField(max_length=20)
    comentario = forms.CharField(max_length=200, required=False)


class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ("monto", "metodo", "tipo", "referencia")
        widgets = {"referencia": forms.TextInput(attrs={"placeholder": "N° operación"})}


class DespachoForm(forms.ModelForm):
    class Meta:
        model = Despacho
        fields = ("pedido", "repartidor", "direccion", "observaciones")
        widgets = {"observaciones": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pedido"].queryset = Pedido.objects.filter(
            estado="listo", modalidad="despacho"
        ).select_related("cliente")
        self.fields["repartidor"].queryset = User.objects.filter(
            perfil__rol__in=["despacho", "admin"]
        ).order_by("first_name")
        self.fields["repartidor"].required = False


class ConfirmarEntregaForm(forms.Form):
    receptor_nombre = forms.CharField(max_length=120, label="Quién recibe")
    observaciones = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2})
    )
    firma = forms.ImageField(required=False, label="Firma digital")
    comprobante = forms.ImageField(
        required=False, label="Comprobante fotográfico"
    )

    def clean(self):
        datos = super().clean()
        if not (datos.get("firma") or datos.get("comprobante")):
            raise forms.ValidationError(
                "Adjunta la firma digital o el comprobante fotográfico."
            )
        return datos


class SeguimientoForm(forms.Form):
    codigo = forms.CharField(
        max_length=40,
        label="Código o enlace de seguimiento",
        widget=forms.TextInput(attrs={"placeholder": "PED-00042"}),
    )


class UsuarioInternoForm(forms.Form):
    """Alta de un usuario del equipo interno desde el panel de gestión."""

    ROLES_INTERNOS = [
        (clave, etiqueta)
        for clave, etiqueta in Perfil.ROLES
        if clave != "cliente"
    ]

    nombre = forms.CharField(max_length=60, label="Nombre")
    apellido = forms.CharField(max_length=60, label="Apellido")
    username = forms.CharField(max_length=30, label="Usuario")
    email = forms.EmailField(label="Correo")
    telefono = forms.CharField(max_length=20, required=False, label="Teléfono")
    rol = forms.ChoiceField(choices=ROLES_INTERNOS, label="Rol")
    turno = forms.ChoiceField(
        choices=[("", "Sin turno definido"), *Perfil.TURNOS],
        required=False,
        label="Turno",
    )
    especialidad = forms.CharField(
        max_length=80,
        required=False,
        label="Especialidad",
        widget=forms.TextInput(attrs={"placeholder": "Repostería, reparto, control…"}),
    )
    zona = forms.CharField(
        max_length=80,
        required=False,
        label="Zona",
        widget=forms.TextInput(attrs={"placeholder": "Solo despacho"}),
    )
    vehiculo = forms.CharField(
        max_length=60,
        required=False,
        label="Vehículo",
        widget=forms.TextInput(attrs={"placeholder": "Solo despacho"}),
    )
    notas = forms.CharField(
        max_length=200,
        required=False,
        label="Notas",
        widget=forms.TextInput(attrs={"placeholder": "Observaciones del equipo"}),
    )
    password1 = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    password2 = forms.CharField(
        widget=forms.PasswordInput, label="Repetir contraseña"
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Ese usuario ya está en uso.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con ese correo.")
        return email

    def clean(self):
        datos = super().clean()
        clave = datos.get("password1")
        if clave and clave != datos.get("password2"):
            self.add_error("password2", "Las contraseñas no coinciden.")
        if clave:
            try:
                validate_password(clave)
            except forms.ValidationError as error:
                self.add_error("password1", error)
        rol = datos.get("rol")
        if rol != "despacho":
            datos["zona"] = ""
            datos["vehiculo"] = ""
        return datos


class ClienteCuentaForm(forms.ModelForm):
    """Ficha de cliente con cuenta de tienda opcional."""

    username = forms.CharField(
        max_length=30,
        required=False,
        label="Usuario (opcional)",
        help_text="Déjalo vacío para crear solo la ficha de mostrador.",
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput, required=False, label="Contraseña"
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput, required=False, label="Repetir contraseña"
    )

    class Meta:
        model = Cliente
        fields = ("nombre", "telefono", "email", "direccion")
        widgets = {"direccion": forms.TextInput(attrs={"placeholder": "Calle y número"})}

    def clean(self):
        datos = super().clean()
        username = (datos.get("username") or "").strip()
        clave = datos.get("password1")
        if username:
            if User.objects.filter(username__iexact=username).exists():
                self.add_error("username", "Ese usuario ya está en uso.")
            if not clave:
                self.add_error(
                    "password1", "Indica una contraseña para crear la cuenta."
                )
            elif clave != datos.get("password2"):
                self.add_error("password2", "Las contraseñas no coinciden.")
            elif not (datos.get("email") or "").strip():
                self.add_error(
                    "email", "La cuenta de tienda necesita un correo."
                )
            elif User.objects.filter(
                email__iexact=datos["email"].strip()
            ).exists():
                self.add_error(
                    "email", "Ya existe una cuenta con ese correo."
                )
        return datos


class PedidoEdicionForm(forms.ModelForm):
    """Edición de la cabecera de un pedido (no cambia el estado)."""

    class Meta:
        model = Pedido
        fields = (
            "cliente",
            "canal",
            "modalidad",
            "fecha_entrega",
            "direccion_entrega",
            "telefono_contacto",
            "descripcion_diseno",
            "costo_despacho",
            "observaciones",
            "retirado_por",
        )
        widgets = {
            "fecha_entrega": DATE_INPUT,
            "descripcion_diseno": forms.Textarea(attrs={"rows": 3}),
            "observaciones": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha_entrega"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["cliente"].queryset = Cliente.objects.order_by("nombre")


PedidoDetalleFormSet = inlineformset_factory(
    Pedido,
    PedidoDetalle,
    fields=("producto", "cantidad", "precio_unitario", "personalizacion"),
    extra=1,
    can_delete=True,
    widgets={"personalizacion": forms.Textarea(attrs={"rows": 2})},
)


class VentaMostradorForm(forms.Form):
    """Cierre de una venta directa de mostrador.

    Permite elegir un cliente existente o crear uno nuevo con los datos
    mínimos, definir si el cliente se lo lleva o si sale a delivery y registrar
    el pago recibido en el momento.
    """

    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.order_by("nombre"),
        required=False,
        label="Cliente registrado",
        empty_label="— Cliente nuevo o sin ficha —",
    )
    nuevo_nombre = forms.CharField(
        max_length=120, required=False, label="Nombre del cliente nuevo"
    )
    nuevo_telefono = forms.CharField(
        max_length=20, required=False, label="Teléfono"
    )
    nuevo_email = forms.EmailField(required=False, label="Correo")
    nueva_direccion = forms.CharField(
        max_length=200, required=False, label="Dirección del cliente"
    )

    tipo = forms.ChoiceField(
        choices=[
            ("retiro", "Se lo lleva el cliente (retiro en tienda)"),
            ("delivery", "Despacho delivery a domicilio"),
        ],
        initial="retiro",
        widget=forms.RadioSelect,
        label="Tipo de venta",
    )
    direccion_entrega = forms.CharField(
        max_length=200, required=False, label="Dirección de entrega"
    )
    retirado_por = forms.CharField(
        max_length=120, required=False, label="¿Quién retira?"
    )

    monto = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        initial=0,
        label="Pago recibido",
        help_text="Déjalo en 0 si queda saldo pendiente.",
    )
    metodo = forms.ChoiceField(
        choices=Pago.METODOS, initial="efectivo", label="Método de pago"
    )
    observaciones = forms.CharField(
        max_length=200,
        required=False,
        label="Observaciones",
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def clean(self):
        datos = super().clean()
        cliente = datos.get("cliente")
        nombre = (datos.get("nuevo_nombre") or "").strip()
        telefono = (datos.get("nuevo_telefono") or "").strip()
        if not cliente and not (nombre and telefono):
            raise forms.ValidationError(
                "Elige un cliente registrado o escribe nombre y teléfono para "
                "crear uno nuevo."
            )
        if datos.get("tipo") == "delivery":
            direccion = (datos.get("direccion_entrega") or "").strip()
            if not direccion:
                self.add_error(
                    "direccion_entrega",
                    "El delivery necesita una dirección de entrega.",
                )
        return datos

