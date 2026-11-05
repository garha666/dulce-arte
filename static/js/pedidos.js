/* Listado y creación de pedidos consumiendo la API DRF */

function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[2]) : null;
}

function escapeHtml(value) {
    const text = value == null ? "" : String(value);
    return text.replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    })[char]);
}

const ETIQUETAS = {
    recibido: "Recibido",
    preparacion: "En preparación",
    horneado: "Horneado / Decorado",
    calidad: "Control de calidad",
    listo: "Listo",
    despachado: "Despachado",
    entregado: "Entregado",
    cancelado: "Cancelado",
};

async function cargarPedidos() {
    const cuerpo = document.querySelector("#tabla-pedidos tbody");
    if (!cuerpo) return;

    const respuesta = await fetch("/api/pedidos/");
    if (!respuesta.ok) {
        cuerpo.innerHTML = '<tr><td colspan="5" class="empty">No se pudo cargar la lista.</td></tr>';
        return;
    }
    const datos = await respuesta.json();
    const pedidos = datos.results || datos;

    if (!pedidos.length) {
        cuerpo.innerHTML = '<tr><td colspan="5" class="empty">Aún no hay pedidos registrados.</td></tr>';
        return;
    }

    cuerpo.innerHTML = pedidos
        .map((p) => {
            const fecha = new Date(p.fecha_entrega).toLocaleString("es-CL", {
                day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
            });
            const estado = escapeHtml(p.estado);
            const etiqueta = escapeHtml(ETIQUETAS[p.estado] || p.estado);
            return `<tr>
                <td><a href="/pedidos/${Number(p.id)}/">${escapeHtml(p.codigo)}</a></td>
                <td>${escapeHtml(p.cliente_nombre)}</td>
                <td>${fecha}</td>
                <td><span class="badge estado-${estado}">${etiqueta}</span></td>
                <td>$${Number(p.total).toLocaleString("es-CL")}</td>
            </tr>`;
        })
        .join("");
}

const formPedido = document.querySelector("#form-pedido");

if (formPedido) {
    formPedido.addEventListener("submit", async (evento) => {
        evento.preventDefault();
        const form = evento.target;
        const msg = document.querySelector("#form-msg");
        const datos = new FormData(form);

        const payload = {
            cliente: Number(datos.get("cliente")),
            fecha_entrega: datos.get("fecha_entrega"),
            descripcion_diseno: datos.get("descripcion_diseno") || "",
            anticipo: datos.get("anticipo") || "0",
            costo_despacho: datos.get("costo_despacho") || "0",
            detalles: [
                {
                    producto: Number(datos.get("producto")),
                    cantidad: Number(datos.get("cantidad")),
                },
            ],
        };

        msg.textContent = "Guardando…";
        const respuesta = await fetch("/api/pedidos/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"),
            },
            body: JSON.stringify(payload),
        });

        if (!respuesta.ok) {
            const error = await respuesta.json();
            const detalle = error.detail || error;
            msg.textContent = "No se pudo registrar: " +
                (Array.isArray(detalle) ? detalle.join(" ") : JSON.stringify(detalle));
            return;
        }

        msg.textContent = "Pedido registrado correctamente.";
        form.reset();
        cargarPedidos();
    });
}

cargarPedidos();
