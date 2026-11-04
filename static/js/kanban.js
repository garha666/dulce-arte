/* Tablero Kanban: mueve pedidos contra la API DRF */

function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[2]) : null;
}

async function cambiarEstado(pedidoId, nuevoEstado, boton) {
    boton.disabled = true;
    try {
        const respuesta = await fetch(`/api/pedidos/${pedidoId}/cambiar_estado/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"),
            },
            body: JSON.stringify({ estado: nuevoEstado }),
        });

        if (!respuesta.ok) {
            const error = await respuesta.json();
            const detalle = error.detail || error;
            alert("No se pudo mover el pedido:\n" + (Array.isArray(detalle) ? detalle.join("\n") : JSON.stringify(detalle)));
            boton.disabled = false;
            return;
        }
        window.location.reload();
    } catch (e) {
        alert("Error de conexión con la API: " + e.message);
        boton.disabled = false;
    }
}

document.querySelectorAll("[data-cambiar]").forEach((boton) => {
    boton.addEventListener("click", () => {
        cambiarEstado(boton.dataset.cambiar, boton.dataset.estado, boton);
    });
});
