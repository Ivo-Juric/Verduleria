// Autocompletar - archivo: static/js/main.js (reemplazar la sección correspondiente)
async function buscarProductos(q) {
    const res = await fetch(`/productos/autocomplete?q=${encodeURIComponent(q)}`);
    return await res.json();
}

document.addEventListener("DOMContentLoaded", () => {
    const input = document.querySelector("#searchProducto");
    const sugerencias = document.querySelector("#sugerencias");
    const hiddenId = document.querySelector("#producto_id_hidden");

    if (input) {
        input.addEventListener("input", async () => {
            const q = input.value.trim();
            if (!q) {
                sugerencias.innerHTML = "";
                hiddenId.value = "";
                return;
            }
            try {
                const items = await buscarProductos(q);
                // Si no hay items
                if (!items || items.length === 0) {
                    sugerencias.innerHTML = "";
                    return;
                }

                sugerencias.innerHTML = items.map(i =>
                    `<div class="list-group-item list-group-item-action"
                          data-id="${i.id}"
                          data-precio="${i.precio}"
                          data-unidad="${i.unidad || ''}"
                          data-nombre="${i.nombre}">
                        <strong>[ID: ${i.id}] ${i.nombre}</strong> —
                        ${i.tiene_oferta ? `<span class="text-decoration-line-through text-muted">$${i.precio_original}</span> <span class="text-success">$${i.precio}</span>` : `$${i.precio}`} / ${i.unidad || ''}
                        ${i.tiene_oferta ? `<br><small class="text-success">${i.descripcion_oferta}</small>` : ''}
                     </div>`
                ).join("");
            } catch (err) {
                console.error("Error al buscar productos:", err);
                sugerencias.innerHTML = "";
            }
        });

        sugerencias.addEventListener("click", e => {
            const item = e.target.closest("[data-id]");
            if (!item) return;
            const id = item.dataset.id;
            const nombre = item.dataset.nombre;
            const precio = item.dataset.precio;
            const unidad = item.dataset.unidad;

            // Ponemos solo el nombre en el input visible
            input.value = nombre;
            // Guardamos el id real en el hidden
            hiddenId.value = id;
            // (opcional) también podés llenar un campo precio si lo tuvieras
            sugerencias.innerHTML = "";
        });

        // Cerrar sugerencias si se hace click fuera
        document.addEventListener("click", (ev) => {
            if (!ev.target.closest("#sugerencias") && ev.target !== input) {
                sugerencias.innerHTML = "";
            }
        });
    }

    // Dark mode (tu código ya)
    const dmBtn = document.getElementById("darkModeToggle");
    if (dmBtn) {
        const current = localStorage.getItem("dm") === "1";
        document.body.classList.toggle("dark", current);

        dmBtn.addEventListener("click", () => {
            const isDark = document.body.classList.toggle("dark");
            localStorage.setItem("dm", isDark ? "1" : "0");
        });
    }
});
