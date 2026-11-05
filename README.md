# Dulce Arte — Sistema de trazabilidad y pedidos

Aplicación web fullstack para una pastelería artesanal: cotización de pedidos personalizados,
tablero Kanban de cocina, descuento automático de insumos por receta (BOM) y despacho con
confirmación de entrega mediante firma digital o comprobante fotográfico.

**Evaluación N°3 — Desarrollo Backend**

- Alumno: Matías Gubelín
- Repositorio: <https://github.com/garha666/dulce-arte>
- Sección: IEC-N4-C1
- Docente: Marcelo Alvarado Aravena
- IP pública AWS EC2: _(completar al desplegar)_

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Django 5.2 + Django REST Framework |
| Base de datos | PostgreSQL 16 (EC2 y Docker local) |
| Frontend | Templates Django + HTML/CSS/JS nativo (fetch) |
| Servidor de aplicación | Gunicorn (socket Unix, servicio systemd) |
| Proxy inverso | Nginx |
| Nube | AWS Academy — instancia EC2 Ubuntu 22.04 + Elastic IP |

## Funcionalidades (las 4 del caso)

1. **Cotización y registro de pedidos**: cliente, productos, diseño, fecha/hora de entrega,
   anticipo y cálculo automático de total y saldo.
2. **Tablero Kanban de cocina**: Recibido → En preparación → Horneado/Decorado →
   Control de calidad → Listo → Despachado → Entregado, con transiciones validadas e historial.
3. **Descuento de insumos por BOM**: al pasar a "En preparación" se descuentan los insumos de la
   receta; si no alcanza el stock, la operación se rechaza y se informan los faltantes.
4. **Despacho con confirmación**: ruta, receptor, firma digital o comprobante fotográfico.

## Estructura

```
dulce-arte/
├── drf/                  # proyecto Django (settings, urls, wsgi)
├── api/                  # app única: modelos, admin, API y vistas HTML
│   ├── models.py         # dominio en 3FN + reglas de negocio
│   ├── admin.py          # Admin personalizado
│   ├── serializers.py
│   ├── views.py          # ViewSets + páginas
│   ├── permissions.py    # permisos de API por rol
│   ├── roles.py          # roles, menús y permisos compartidos
│   ├── context_processors.py
│   └── urls.py
├── templates/            # landing, paneles por rol, kanban, pedidos, inventario, despachos…
├── static/               # css/estilos.css, fonts/ y js (kanban, pedidos)
├── docs/                 # constitución y modelo de datos (3FN)
├── specs/                # especificación SDD (spec, plan, tasks)
├── deploy/               # gunicorn.service, nginx.conf, guía de despliegue
├── seed_data.py          # datos de prueba
├── smoke_test.py         # verificación rápida
└── docker-compose.yml    # PostgreSQL local
```

## Puesta en marcha local

```powershell
# 1. Entorno virtual
python -m venv env
.\env\Scripts\activate
pip install -r requirements.txt

# 2. Variables de entorno
copy .env.example .env      # ajustar credenciales

# 3. Base de datos
docker compose up -d        # PostgreSQL en localhost:5433 (.env ya apunta ahí)
# (alternativa sin Docker: DB_ENGINE=sqlite en .env)

# 4. Migraciones y datos de prueba
python manage.py migrate
python seed_data.py

# 5. Servidor
python manage.py runserver
```

Abrir <http://127.0.0.1:8000/> → landing pública. El panel de gestión está en
<http://127.0.0.1:8000/login/> y muestra métricas distintas según el rol.

### Usuarios de prueba

| Usuario | Clave | Rol |
|---|---|---|
| `admin` | `Dulce2026!` | Administrador (accede a `/admin/`) |
| `ventas` | `Dulce2026!` | Cotizaciones |
| `cocina` | `Dulce2026!` | Kanban de producción |
| `calidad` | `Dulce2026!` | Control de calidad |
| `despacho` | `Dulce2026!` | Reparto |

> Estas claves son solo para la demo local. Cámbialas antes de publicar la instancia EC2.

## Rutas principales

| Ruta | Descripción | Acceso |
|---|---|---|
| `/` | Landing pública; si hay sesión, panel con métricas y alertas | Público / autenticado |
| `/pedidos/` | Registrar pedidos (ventas/admin) y ver el listado | Autenticado |
| `/kanban/` | Tablero de producción y cambio de estados | admin, cocina, calidad |
| `/inventario/` | Stock de insumos y recetas (BOM) | admin, cocina, calidad |
| `/despachos/` | Crear despacho y confirmar entrega con evidencia | admin, despacho |
| `/quienes-somos/`, `/servicios/`, `/contacto/` | Sitio público | Público |
| `/admin/` | Django Admin personalizado | admin |
| `/api/` | Navegador de la API DRF | Autenticado |

## Endpoints de la API

| Método | Endpoint | Descripción | Roles de escritura |
|---|---|---|---|
| GET/POST | `/api/pedidos/` | Listar / crear pedidos (con detalles anidados) | admin, ventas |
| GET/PUT/PATCH/DELETE | `/api/pedidos/{id}/` | CRUD de un pedido (bloqueado tras descontar BOM) | admin, ventas |
| POST | `/api/pedidos/{id}/cambiar_estado/` | Mover en el Kanban (valida flujo y descuenta BOM) | admin, cocina, calidad |
| POST | `/api/pedidos/{id}/descontar_insumos/` | Forzar descuento de insumos | admin, cocina, calidad |
| GET/POST | `/api/clientes/`, `/api/productos/`, `/api/insumos/` | Catálogos | solo admin |
| GET/POST | `/api/despachos/` | Despachos (solo para pedidos listos; valida firma/comprobante) | admin, despacho |
| GET | `/api/movimientos/` | Auditoría de movimientos de insumos | solo lectura |

La API exige sesión iniciada (`IsAuthenticated`) y aplica los mismos roles que las páginas
(`api/permissions.py`). Los roles sin permiso reciben **403**, no un 400 de validación. En el
navegador de DRF se puede iniciar sesión con `/admin/` y volver a `/api/`.

## Reglas de negocio implementadas

- Flujo de estados restringido (`Pedido.TRANSICIONES`); transición inválida → **400**.
- Descuento de insumos **atómico** y **una sola vez** por pedido (`select_for_update` + bandera).
- Stock insuficiente → se cancela el cambio de estado con el listado de faltantes.
- `Pedido.cambiar_estado("entregado")` exige un despacho confirmado con firma o comprobante.
- `Despacho.clean()` y `DespachoSerializer` exigen receptor y evidencia para confirmar.
- Un despacho solo se crea para pedidos en estado **Listo** (RF-13), tanto en la vista HTML como
  en la API; la confirmación es atómica y deja el pedido en **Entregado**.
- No se puede confirmar dos veces el mismo despacho.
- Los pedidos con `insumos_descontados=True` no se pueden editar ni eliminar por la API.
- Permisos por rol compartidos entre HTML y API: ventas no mueve el Kanban ni descuenta insumos;
  cocina/calidad no crean ni borran pedidos o despachos; despacho gestiona sus rutas.
- El listado JS escapa `cliente_nombre` y el código antes de insertarlos en el DOM.

## Verificación

```powershell
python manage.py check
python manage.py test api
python smoke_test.py
```

Resultado esperado: todas las pruebas de `api/tests.py` OK (permisos, despacho, BOM y escape
del frontend), todas las páginas en 200, cambio de estado 200 con descuento de stock y
transición inválida 400. `smoke_test.py` falla de forma explícita si no hay un pedido en estado
`recibido` para probar la transición central.

## Despliegue en AWS EC2

Ver [`deploy/README-despliegue.md`](deploy/README-despliegue.md): Postgres en la instancia,
Gunicorn con socket Unix, Nginx como proxy inverso y estáticos servidos por Nginx.
También hay un script idempotente: `bash deploy/instalar.sh`.

Antes de publicar la instancia:

- Cambiar la clave de los usuarios demo (`admin`, `ventas`, etc.) o no ejecutar el seed
  (`SEED_DEMO_DATA=true` solo para una demo controlada).
- Reemplazar `SECRET_KEY` y la contraseña de PostgreSQL en `.env`; no reutilizar las de ejemplo.
- Mantener `DJANGO_DEBUG=False`, configurar `ALLOWED_HOSTS` con la IP elástica y usar HTTPS
  (Nginx + certificado) para que las cookies de sesión viajen cifradas. Cuando el HTTPS esté
  activo, poner `DJANGO_SECURE_COOKIES=True`; con HTTP simple debe quedar en `False`.
- Rotar las credenciales si el repositorio o la instancia ya estuvieron expuestos.

## Defensa

Guion de demostración y preguntas frecuentes: [`docs/GUION_DEFENSA.md`](docs/GUION_DEFENSA.md).

