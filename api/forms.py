"""Formularios de la tienda y del panel interno.

Toda la validación de negocio vive en los modelos; los formularios solo
recogen los datos y delegan en `full_clean`.
"""

from django import forms
from django.contrib.auth.models import User

from .models import Despacho, Pago, Pedido, Producto

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
