/************************************
Editar transacción
***********************************/
(function () {
    const inputs = {
        date: document.getElementById("id_date"),
        type: document.getElementById("id_type"),
        net_amount: document.getElementById("id_net_amount"),
        commission: document.getElementById("id_commission"),
    };

    // Sin el campo "type" no hay form que manejar
    if (!inputs.type) return;

    const form = inputs.type.closest("form");
    const submitBtn = form.querySelector('button[type="submit"]');
    const titleEl = form.closest(".form").querySelector(".form-title");
    if (!submitBtn) return;

    // "423.880000000000" -> "423.88" | "5.000" -> "5" | "100" -> "100"
    function trimZeros(value) {
        return value.includes(".") ? value.replace(/\.?0+$/, "") : value;
    }

    // Estado original del form de "registrar"
    const originalText = submitBtn.textContent.trim();
    const originalTitle = titleEl ? titleEl.textContent.trim() : "";
    const initial = {};
    Object.entries(inputs).forEach(([k, el]) => { if (el) initial[k] = el.value; });

    // Elementos que solo existen en modo edición
    const hiddenId = document.createElement("input");
    hiddenId.type = "hidden";
    hiddenId.name = "transaction_id";

    const cancelBtn = document.createElement("button");
    cancelBtn.type = "button";
    cancelBtn.className = "btn btn-secondary w-100 ms-1";
    cancelBtn.textContent = "Cancelar";

    function enterEditMode(id) {
        hiddenId.value = id;
        form.appendChild(hiddenId);
        submitBtn.textContent = "Actualizar";
        if (titleEl) titleEl.textContent = "Editar transacción";
        submitBtn.insertAdjacentElement("afterend", cancelBtn);
    }

    function exitEditMode() {
        hiddenId.remove();
        cancelBtn.remove();
        submitBtn.textContent = originalText;
        if (titleEl) titleEl.textContent = originalTitle;
        Object.entries(initial).forEach(([k, v]) => { inputs[k].value = v; });
    }

    // Caso: la validación del servidor falló al actualizar -> la página
    // se recargó con el form ya lleno; solo hay que volver a poner el modo edición
    const editingEl = document.getElementById("editing-transaction-id");
    const editingId = editingEl ? JSON.parse(editingEl.textContent) : null;
    if (editingId) enterEditMode(editingId);

    // Click en el lápiz: cargar datos al form
    document.querySelectorAll(".btn-edit-transaction").forEach(btn => {
        btn.addEventListener("click", () => {
            const d = btn.dataset;
            if (inputs.date) inputs.date.value = d.date;
            inputs.type.value = d.type;
            if (inputs.net_amount) inputs.net_amount.value = trimZeros(d.netAmount);
            if (inputs.commission) inputs.commission.value = trimZeros(d.commission);

            enterEditMode(d.transactionId);
            form.scrollIntoView({ behavior: "smooth", block: "center" });
        });
    });

    cancelBtn.addEventListener("click", () => {
        // Si la página cargó con errores del servidor, lo más limpio es recargar
        if (editingId) {
            window.location.href = window.location.pathname;
            return;
        }
        exitEditMode();
    });
})();