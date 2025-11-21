// Autocompletar
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
                return;
            }
            const items = await buscarProductos(q);
            sugerencias.innerHTML = items.map(i =>
                `<div class="list-group-item list-group-item-action"
                 data-id="${i.id}" data-precio="${i.precio}">
                     ${i.nombre} - $${i.precio} / ${i.unidad}
                 </div>`
            ).join("");
        });

        sugerencias.addEventListener("click", e => {
            const item = e.target.closest("[data-id]");
            if (!item) return;
            input.value = item.innerText;
            hiddenId.value = item.dataset.id;
            sugerencias.innerHTML = "";
        });
    }

    // Dark mode
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
