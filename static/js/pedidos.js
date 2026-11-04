/* Listado y creación de pedidos consumiendo la API DRF */

function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[2]) : null;
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
    const respuesta = await fetch("/api/pedidos/");
    if (!respuesta.ok) {
        cuerpo.innerHTML = '<tr><td colspan="5" class="muted">No se pudo cargar la lista.</td></tr>';
        return;
    }
    const datos = await respuesta.json();
    const pedidos = datos.results || datos;

    if (!pedidos.length) {
        cuerpo.innerHTML = '<tr><td colspan="5" class="muted">Aún no hay pedidos registrados.</td></tr>';
        return;
    }

    cuerpo.innerHTML = pedidos
        .map((p) => {
            const fecha = new Date(p.fecha_entrega).toLocaleString("es-CL", {
                day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
            });
            return `<tr>
                <td><a href="/pedidos/${p.id}/">${p.codigo}</a></td>
                <td>${p.cliente_nombre}</td>
                <td>${fecha}</td>
                <td><span class="badge estado-${p.estado}">${ETIQUETAS[p.estado] || p.estado}</span></td>
                <td>$${Number(p.total).toLocaleString("es-CL")}</td>
            </tr>`;
        })
        .join("");
}

document.querySelector("#form-pedido").addEventListener("submit", async (evento) => {
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
        msg.textContent = "Error: " + JSON.stringify(error);
        return;
    }

    msg.textContent = "Pedido registrado correctamente.";
    form.reset();
    cargarPedidos();
});

cargarPedidos();
