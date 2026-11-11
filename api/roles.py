"""Roles, menús y permisos de navegación de Dulce Arte.

Centraliza qué puede ver cada rol para que las vistas HTML y los templates
no repitan condicionales.
"""

from .models import Pedido, Perfil

ETIQUETAS_ROL = dict(Perfil.ROLES)

# Roles autorizados por área. Se usan tanto en las vistas HTML como en la API.
ROLES_ADMIN = frozenset({"admin"})
ROLES_PRODUCCION = frozenset({"admin", "cocina", "calidad"})
ROLES_PEDIDOS = frozenset({"admin", "ventas"})
ROLES_DESPACHO = frozenset({"admin", "despacho"})
ROLES_INTERNOS = frozenset({"admin", "ventas", "cocina", "calidad", "despacho"})
ROLES_EQUIPO = frozenset({"admin"})


def _transiciones_de(rol):
    """Lista legible de transiciones que el rol puede ejecutar (desde el modelo)."""
    etiquetas = dict(Pedido.ESTADOS)
    resultado = []
    for origen, destinos in Pedido.TRANSICIONES_ROL.items():
        for destino, roles in destinos.items():
            if rol in roles:
                resultado.append(f"{etiquetas[origen]} → {etiquetas[destino]}")
    return resultado


# Guía funcional de cada rol: qué recibe, qué hace y qué no puede hacer.
ROLES_INFO = {
    "admin": {
        "etiqueta": "Administrador",
        "resumen": "Dueño del sistema: configura el catálogo, el equipo y supervisa toda la operación.",
        "atributos": ["Acceso al panel interno, al Admin de Django y a la API"],
        "responsabilidades": [
            "Crear usuarios internos y clientes, y asignar su rol.",
            "Mantener productos, precios, recetas (BOM) e insumos.",
            "Supervisar pedidos, pagos, producción y despachos.",
            "Resolver excepciones y auditorías de cualquier área.",
        ],
        "permisos": [
            "Todas las páginas internas y todas las transiciones.",
            "Admin de Django y API REST administrativa.",
            "Crear y editar pedidos, pagos, despachos y equipo.",
        ],
        "limites": [
            "No puede entregar sin evidencia ni retiro sin responsable.",
            "No puede editar un pedido con insumos ya descontados.",
        ],
        "atributo_clave": "Sin atributos operativos: su alcance es transversal.",
    },
    "ventas": {
        "etiqueta": "Ventas / Cotizaciones",
        "resumen": "Atiende al cliente, vende en mostrador, registra pedidos y cobra el anticipo antes de producir.",
        "atributos": ["Turno", "Especialidad (mostrador, cotizaciones, eventos)"],
        "responsabilidades": [
            "Vender en mostrador productos de vitrina con stock disponible.",
            "Registrar pedidos de mostrador y revisar los de la tienda.",
            "Contactar al cliente, ajustar la agenda y la personalización.",
            "Registrar pagos y confirmar el pedido cuando hay abono.",
            "Cancelar pedidos y cerrar retiros o ventas con delivery.",
        ],
        "permisos": [
            "Mostrador: armar la venta, crear o elegir cliente y cobrar.",
            "Pedidos: crear, editar (antes del BOM), confirmar y cancelar.",
            "Listo → Despachado (crea la ruta si falta) y Listo → Entregado (retiro).",
            "Registrar pagos y cerrar retiros con el nombre de quien retira.",
        ],
        "limites": [
            "No mueve pedidos en preparación, horneado ni calidad.",
            "No confirma entregas a domicilio con firma o comprobante.",
            "No accede al Admin de Django ni a la API.",
        ],
        "atributo_clave": "Turno: define quién atiende mostrador y teléfono.",
    },
    "cocina": {
        "etiqueta": "Cocina",
        "resumen": "Produce el pedido: descuenta insumos, hornea, decora y lo envía a calidad.",
        "atributos": ["Turno", "Especialidad (repostería, decoración, panadería)"],
        "responsabilidades": [
            "Iniciar la preparación (descuenta los insumos de la receta).",
            "Avanzar a horneado/decorado y luego a control de calidad.",
            "Revisar disponibilidad de insumos y reportar faltantes.",
            "Devolver a preparación si calidad detecta un problema.",
        ],
        "permisos": [
            "Confirmado → En preparación → Horneado → Calidad.",
            "Calidad → En preparación (corrección).",
        ],
        "limites": [
            "No confirma pedidos ni registra pagos.",
            "No cancela pedidos (lo hace ventas o administración).",
            "No despacha ni entrega.",
        ],
        "atributo_clave": "Especialidad: asigna tortas, postres o mesas dulces.",
    },
    "calidad": {
        "etiqueta": "Control de calidad",
        "resumen": "Verifica terminación, porciones y presentación antes de declarar el pedido listo.",
        "atributos": ["Turno", "Especialidad (control sensorial, inocuidad)"],
        "responsabilidades": [
            "Revisar cada pedido en la columna Calidad.",
            "Aprobar y pasar a Listo, o devolver a preparación con observación.",
            "Dejar registro en el historial del pedido.",
        ],
        "permisos": [
            "Calidad → Listo (aprobación).",
            "Calidad → En preparación (devolución).",
        ],
        "limites": [
            "No inicia producción ni hornea.",
            "No confirma, cobra, despacha ni entrega.",
        ],
        "atributo_clave": "Turno: cobertura del control antes de cada entrega.",
    },
    "despacho": {
        "etiqueta": "Despacho",
        "resumen": "Asigna rutas, entrega a domicilio y cierra la entrega con evidencia o retiro.",
        "atributos": ["Turno", "Zona asignada", "Vehículo"],
        "responsabilidades": [
            "Crear la ruta de un pedido listo y marcarlo como despachado.",
            "Confirmar la entrega con receptor y firma o comprobante.",
            "Registrar retiros en tienda indicando quién retira.",
        ],
        "permisos": [
            "Listo → Despachado (crear ruta).",
            "Despachado → Entregado (con evidencia).",
            "Listo → Entregado (retiro con responsable).",
        ],
        "limites": [
            "No confirma pedidos ni registra pagos.",
            "No modifica la producción ni el catálogo.",
        ],
        "atributo_clave": "Zona y vehículo: definen qué rutas puede tomar.",
    },
    "cliente": {
        "etiqueta": "Cliente",
        "resumen": "Compra en la tienda, sigue sus pedidos y consulta el estado de su cuenta.",
        "atributos": ["Teléfono", "Dirección de despacho"],
        "responsabilidades": [
            "Armar el carrito y reservar una fecha con 48 h de anticipación.",
            "Pagar el anticipo acordado y recibir su pedido.",
        ],
        "permisos": [
            "Catálogo, carrito, checkout y seguimiento público.",
            "Ver solo sus propios pedidos.",
        ],
        "limites": [
            "No accede a ninguna pantalla interna.",
            "No ve pedidos de otros clientes ni la API.",
        ],
        "atributo_clave": "Dirección: solo se usa si elige despacho a domicilio.",
    },
}

# Cada ítem: (nombre de URL, texto del menú)
MENUS = {
    "admin": [
        ("home", "Panel"),
        ("mostrador", "Mostrador"),
        ("pedidos", "Pedidos"),
        ("kanban", "Cocina"),
        ("inventario", "Insumos"),
        ("despachos", "Despachos"),
        ("equipo", "Equipo"),
        ("tienda", "Tienda"),
    ],
    "ventas": [
        ("home", "Panel"),
        ("mostrador", "Mostrador"),
        ("pedidos", "Pedidos"),
        ("tienda", "Tienda"),
        ("contacto", "Contacto"),
    ],
    "cocina": [
        ("home", "Panel"),
        ("kanban", "Cocina"),
        ("inventario", "Insumos"),
        ("pedidos", "Pedidos"),
    ],
    "calidad": [
        ("home", "Panel"),
        ("kanban", "Cocina"),
        ("inventario", "Insumos"),
        ("pedidos", "Pedidos"),
    ],
    "despacho": [
        ("home", "Panel"),
        ("despachos", "Despachos"),
        ("pedidos", "Pedidos"),
    ],
    "cliente": [
        ("tienda", "Tienda"),
        ("mis_pedidos", "Mis pedidos"),
        ("seguimiento", "Seguir pedido"),
    ],
}


def rol_de(user):
    """Devuelve el rol efectivo del usuario (o None si no inició sesión)."""
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser or user.is_staff:
        return "admin"
    perfil = getattr(user, "perfil", None)
    return perfil.rol if perfil else "cliente"


def etiqueta_rol(user):
    rol = rol_de(user)
    return ETIQUETAS_ROL.get(rol, "")


def menu_para(user):
    """Ítems del menú que corresponden al rol del usuario."""
    return MENUS.get(rol_de(user), [])


def puede(user, *roles):
    """True si el rol del usuario está dentro de los roles permitidos."""
    return rol_de(user) in roles


def puede_transicion(user, pedido, nuevo_estado):
    """True si el rol del usuario puede ejecutar esa transición del pedido."""
    return rol_de(user) in pedido.TRANSICIONES_ROL.get(pedido.estado, {}).get(
        nuevo_estado, ()
    )


# Completar la guía con las transiciones reales y el menú de cada rol.
for _rol, _info in ROLES_INFO.items():
    _info["transiciones"] = _transiciones_de(_rol)
    _info["menu"] = MENUS.get(_rol, [])

