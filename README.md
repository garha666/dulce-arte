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
│   ├── permissions.py
│   └── urls.py
├── templates/            # base, home, kanban, pedidos, inventario, despachos, contacto…
├── static/               # css/estilos.css y js (kanban, pedidos)
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

Abrir <http://127.0.0.1:8000/> → redirige a `/login/`.

### Usuarios de prueba

| Usuario | Clave | Rol |
|---|---|---|
| `admin` | `Dulce2026!` | Administrador (accede a `/admin/`) |
| `ventas` | `Dulce2026!` | Cotizaciones |
| `cocina` | `Dulce2026!` | Kanban de producción |
| `calidad` | `Dulce2026!` | Control de calidad |
| `despacho` | `Dulce2026!` | Reparto |

## Rutas principales

| Ruta | Descripción |
|---|---|
| `/` | Panel con métricas y alertas de stock |
| `/pedidos/` | Registrar pedidos y ver el listado |
| `/kanban/` | Tablero de producción (mueve estados) |
| `/inventario/` | Stock de insumos y recetas (BOM) |
| `/despachos/` | Crear despacho y confirmar entrega |
| `/quienes-somos/`, `/servicios/`, `/contacto/` | Sitio público |
| `/admin/` | Django Admin personalizado |
| `/api/` | Navegador de la API DRF |

## Endpoints de la API

| Método | Endpoint | Descripción |
|---|---|---|
| GET/POST | `/api/pedidos/` | Listar / crear pedidos (con detalles anidados) |
| GET/PUT/PATCH/DELETE | `/api/pedidos/{id}/` | CRUD de un pedido |
| POST | `/api/pedidos/{id}/cambiar_estado/` | Mover en el Kanban (valida flujo y descuenta BOM) |
| POST | `/api/pedidos/{id}/descontar_insumos/` | Forzar descuento de insumos |
| GET/POST | `/api/clientes/`, `/api/productos/`, `/api/insumos/` | Catálogos |
| GET/POST | `/api/despachos/` | Despachos (valida firma/comprobante) |
| GET | `/api/movimientos/` | Auditoría de movimientos de insumos |

La API exige sesión iniciada (`IsAuthenticated`). En el navegador de DRF se puede iniciar
sesión con `/admin/` y volver a `/api/`.

## Reglas de negocio implementadas

- Flujo de estados restringido (`Pedido.TRANSICIONES`); transición inválida → **400**.
- Descuento de insumos **atómico** y **una sola vez** por pedido (`select_for_update` + bandera).
- Stock insuficiente → se cancela el cambio de estado con el listado de faltantes.
- `Despacho.clean()` impide confirmar la entrega sin firma o comprobante.
- Permisos por rol: solo cocina/calidad/admin mueven el Kanban (`api/permissions.py`).

## Verificación

```powershell
python manage.py check
python manage.py test api
python smoke_test.py
```

Resultado esperado: 9 pruebas OK, todas las páginas en 200, cambio de estado 200 con descuento
de stock y transición inválida 400.

## Despliegue en AWS EC2

Ver [`deploy/README-despliegue.md`](deploy/README-despliegue.md): Postgres en la instancia,
Gunicorn con socket Unix, Nginx como proxy inverso y estáticos servidos por Nginx.
También hay un script idempotente: `bash deploy/instalar.sh`.

## Defensa

Guion de demostración y preguntas frecuentes: [`docs/GUION_DEFENSA.md`](docs/GUION_DEFENSA.md).

