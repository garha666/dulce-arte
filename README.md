# Dulce Arte — Tienda de pastelería y trazabilidad de pedidos

Aplicación web fullstack para una pastelería artesanal: catálogo público con carrito y checkout,
reserva de cupos con anticipación, pago de anticipo, seguimiento del pedido, tablero Kanban de
cocina, descuento de insumos por receta (BOM), despacho con evidencia y panel interno por roles.
La API REST queda reservada a administración; el resto del equipo y los clientes trabajan con
páginas Django server-side.

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
| Frontend | Templates Django + HTML/CSS/JS nativo (sin frameworks ni fetch a la API) |
| Servidor de aplicación | Gunicorn (socket Unix, servicio systemd) |
| Proxy inverso | Nginx |
| Nube | AWS Academy — instancia EC2 Ubuntu 22.04 + Elastic IP |

## Funcionalidades

1. **Tienda en línea**: catálogo por categorías, disponibilidad calculada desde el BOM, carrito en
   sesión, checkout con retiro o despacho, seguimiento público y cuenta de cliente.
2. **Agenda real**: 48 horas de anticipación para pedidos web, horario 09:00–18:59 de Santiago y
   cupo diario de 6 pedidos; el mostrador puede agendar sin anticipación pero respeta horario y cupo.
3. **Pagos**: registro de abonos por efectivo, transferencia o tarjeta; `estado_pago` y `saldo` se
   calculan desde los pagos y ningún pedido entra a producción sin pago registrado.
4. **Tablero Kanban de cocina**: Recibido → Confirmado → En preparación → Horneado/Decorado →
   Control de calidad → Listo → Despachado → Entregado, con historial y transiciones validadas.
5. **Descuento de insumos por BOM**: al pasar a “En preparación” se descuentan los insumos de la
   receta; si falta stock se rechaza, y una cancelación repone lo consumido.
6. **Despacho y retiro**: la ruta deja el pedido en `despachado`; la entrega se cierra con firma o
   comprobante. El retiro exige registrar quién retira.
7. **Panel interno por roles**: ventas, cocina, calidad y despacho con formularios Django; sin
   llamadas a la API. Cada rol ve solo las transiciones que le corresponden.
8. **Gestión de equipo y clientes**: pantalla `/equipo/` para crear usuarios internos con rol,
   turno, especialidad, zona y vehículo; creación de clientes con o sin cuenta de tienda.
9. **Catálogo con imágenes**: foto propia subida desde el Admin o imagen de demostración incluida
   en `static/IMAGES/productos/`; miniatura en el listado del Admin.
10. **Edición de pedidos**: ventas/admin corrigen cabecera y productos mientras el pedido no haya
    descontado insumos, sin saltarse la máquina de estados.
11. **API administrativa**: DRF disponible solo para el rol administrador, con acciones
    `cambiar_estado` y `descontar_insumos`.

## Estructura

```
dulce-arte/
├── drf/                  # proyecto Django (settings, urls, wsgi)
├── api/                  # app única: dominio, tienda, panel y API
│   ├── models.py         # dominio en 3FN + agenda, pagos y reglas de negocio
│   ├── carrito.py        # carrito en sesión con precios frescos
│   ├── forms.py          # formularios de tienda y panel interno
│   ├── views.py          # tienda, cuenta, panel, acciones y ViewSets
│   ├── serializers.py
│   ├── permissions.py    # EsAdministrador: única llave de la API
│   ├── roles.py          # roles, menús y permisos de navegación
│   ├── context_processors.py
│   ├── admin.py          # Admin personalizado
│   ├── migrations/
│   └── urls.py
├── templates/            # tienda, cuenta, paneles por rol, equipo y sitio público
├── static/               # css/estilos.css, fonts/ e IMAGES/productos/ (fotos demo)
├── docs/                 # constitución, modelo de datos, guion y ADRs
├── specs/                # especificaciones SDD 001 y 002
├── deploy/               # gunicorn.service, nginx.conf, guía de despliegue
├── seed_data.py          # datos de prueba (incluye cliente demo)
├── smoke_test.py         # verificación rápida no destructiva
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

Abrir <http://127.0.0.1:8000/> → landing pública. La tienda está en `/tienda/`, el panel interno
en `/login/` y el Admin de Django en `/admin/`.

### Usuarios de prueba

| Usuario | Clave | Rol |
|---|---|---|
| `admin` | `Dulce2026!` | Administrador (panel, Admin y API) |
| `ventas` | `Dulce2026!` | Pedidos, pagos y confirmación |
| `cocina` | `Dulce2026!` | Kanban de producción |
| `calidad` | `Dulce2026!` | Control de calidad |
| `despacho` | `Dulce2026!` | Reparto y retiros |
| `cliente` | `Cliente2026!` | Cliente demo con historial |

> Estas claves son solo para la demo local. Cámbialas antes de publicar la instancia EC2.

### Roles en una línea

| Rol | Qué hace | Qué no puede hacer |
|---|---|---|
| Administrador | Configura catálogo, equipo, pagos y toda la operación | Entregar sin evidencia o editar pedidos con BOM descontado |
| Ventas | Registra pedidos, cobra anticipos, confirma y cancela | Iniciar producción, despachar o crear rutas |
| Cocina | Inicia preparación, hornea y envía a calidad | Confirmar pagos, cancelar o entregar |
| Calidad | Aprueba el paso a Listo o devuelve a preparación | Producir, cobrar o despachar |
| Despacho | Crea rutas, entrega con evidencia y registra retiros | Confirmar pedidos o modificar producción |
| Cliente | Compra, sigue sus pedidos y ve solo los propios | Entrar al panel interno o a la API |

La guía completa (atributos, responsabilidades, permisos y transiciones reales) está en
`/equipo/` y en `api/roles.py`.

## Rutas principales

| Ruta | Descripción | Acceso |
|---|---|---|
| `/` | Landing pública; con sesión interna, panel según rol | Público |
| `/tienda/` | Catálogo con filtros por categoría y disponibilidad | Público |
| `/tienda/<id>/` | Detalle del producto, receta y personalización | Público |
| `/carrito/` | Carrito en sesión y resumen | Público |
| `/checkout/` | Datos de entrega, agenda y forma de pago | Público |
| `/seguimiento/` | Seguimiento por código o token | Público |
| `/registro/` | Crear cuenta de cliente | Público |
| `/mis-pedidos/` | Historial del cliente autenticado | Cliente |
| `/pedidos/` | Listado, alta de mostrador y filtros | admin, ventas, cocina, calidad, despacho |
| `/pedidos/<id>/` | Detalle, pagos y transiciones según rol | Dueño o personal interno |
| `/pedidos/<id>/editar/` | Corregir cabecera y productos antes del BOM | admin, ventas |
| `/kanban/` | Tablero de producción | admin, cocina, calidad |
| `/inventario/` | Stock de insumos y recetas (BOM) | admin, cocina, calidad |
| `/equipo/` | Guía de roles, alta de equipo y clientes | admin |
| `/despachos/` | Rutas, evidencia de entrega y retiros | admin, despacho |
| `/health/` | Sonda de salud (app + base de datos) | Público |
| `/quienes-somos/`, `/servicios/`, `/contacto/` | Sitio público | Público |
| `/admin/` | Django Admin personalizado | admin |
| `/api/` | API DRF | **solo admin** |

## API administrativa

La API existe para integraciones y automatizaciones del administrador; no es el canal del
personal operativo. El permiso global es `api.permissions.EsAdministrador`: un usuario
autenticado sin rol `admin` recibe **403** y un visitante **401/403**.

| Método | Endpoint | Descripción |
|---|---|---|
| GET/POST | `/api/pedidos/` | Listar / crear pedidos con detalles anidados |
| GET/PUT/PATCH/DELETE | `/api/pedidos/{id}/` | CRUD (no elimina pedidos con insumos descontados) |
| POST | `/api/pedidos/{id}/cambiar_estado/` | Mover en el Kanban validando el flujo |
| POST | `/api/pedidos/{id}/descontar_insumos/` | Forzar el descuento del BOM |
| GET/POST | `/api/clientes/`, `/api/productos/`, `/api/insumos/` | Catálogos |
| GET/POST | `/api/despachos/` | Rutas y confirmación de entrega |
| GET/POST | `/api/pagos/` | Abonos registrados |
| GET | `/api/movimientos/` | Auditoría de inventario |

> Las pantallas internas y la tienda **no** usan `fetch` ni `/api/`: todo se resuelve con
> formularios y render del servidor. Lo verifica `FrontendSeguridadTest`.

## Reglas de negocio implementadas

- Flujo restringido (`Pedido.TRANSICIONES`); transición inválida → error y sin cambios.
- Producción no arranca sin `confirmado`; `confirmado` exige al menos un pago registrado.
- Descuento de insumos **atómico** y **una sola vez** (`select_for_update` + bandera).
- Cancelación con insumos descontados → movimientos de entrada que reponen el stock.
- Agenda: 48 h para pedidos web, 09:00–18:59 en `America/Santiago` y cupo de 6 por día; el cupo
  se cuenta con rango de fecha local para no desplazarse por UTC.
- Despacho a domicilio exige dirección; retiro no tiene costo y el despacho cuesta $3.500.
- Crear ruta → pedido `despachado`; confirmar con receptor y firma/comprobante → `entregado`.
- Retiro → `entregado` solo con `retirado_por` registrado.
- `estado_pago` y `saldo` se derivan de `Pago`, con `anticipo` solo como respaldo histórico.
- Los pedidos con `insumos_descontados=True` no se pueden eliminar por la API.
- Un cliente solo ve sus pedidos; el seguimiento público no expone datos personales.

## Verificación

```powershell
python manage.py check
python manage.py test api
python smoke_test.py
```

Resultado esperado: `manage.py check` sin errores, **54 pruebas OK** en `api/tests.py` (flujo,
pagos, agenda, despacho, tienda, cuenta, permisos por rol, equipo, edición de pedidos, imágenes,
health, API admin-only, BOM y frontend) y `smoke_test.py` con todas las páginas en 200, 403 para
ventas/cocina/cliente en la API y descuento/reposición de stock dentro de una transacción con
rollback.

## Despliegue en AWS EC2

Ver [`deploy/README-despliegue.md`](deploy/README-despliegue.md): Postgres en la instancia,
Gunicorn con socket Unix, Nginx como proxy inverso y estáticos servidos por Nginx.
También hay un script idempotente: `bash deploy/instalar.sh`.

Antes de publicar la instancia:

- Cambiar la clave de los usuarios demo (`admin`, `ventas`, `cliente`, etc.) o no ejecutar el seed
  (`SEED_DEMO_DATA=true` solo para una demo controlada).
- Reemplazar `SECRET_KEY` y la contraseña de PostgreSQL en `.env`; no reutilizar las de ejemplo.
- Mantener `DJANGO_DEBUG=False`, configurar `ALLOWED_HOSTS` con la IP elástica y usar HTTPS
  (Nginx + certificado) para que las cookies de sesión viajen cifradas. Cuando el HTTPS esté
  activo, poner `DJANGO_SECURE_COOKIES=True`; con HTTP simple debe quedar en `False`.
- Rotar las credenciales si el repositorio o la instancia ya estuvieron expuestos.

## Defensa

Guion de demostración y preguntas frecuentes: [`docs/GUION_DEFENSA.md`](docs/GUION_DEFENSA.md).
Decisiones de arquitectura: [`docs/adr/`](docs/adr/). Vocabulario del dominio:
[`GLOSSARY.md`](GLOSSARY.md).
