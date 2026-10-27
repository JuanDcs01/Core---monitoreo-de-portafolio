/************************************
Móvil: formularios como hoja inferior
------------------------------------
En pantallas ≤ 767px los formularios marcados con [data-sheet] se abren desde
un botón flotante ([data-sheet-open]) o al pulsar "editar". En escritorio no
hace nada: el formulario sigue en su lugar de siempre.
************************************/
(function () {
    const sheets = Array.from(document.querySelectorAll('[data-sheet]'));
    if (!sheets.length) return;

    const mq = window.matchMedia('(max-width: 767.98px)');

    const backdrop = document.createElement('div');
    backdrop.className = 'sheet-backdrop';
    document.body.appendChild(backdrop);

    let current = null;

    function close() {
        if (!current) return;
        current.classList.remove('is-open');
        backdrop.classList.remove('is-open');
        document.body.classList.remove('sheet-lock');
        current = null;
    }

    function open(sheet) {
        if (!mq.matches) return;
        close();
        sheet.classList.add('is-open');
        backdrop.classList.add('is-open');
        document.body.classList.add('sheet-lock');
        current = sheet;
    }

    sheets.forEach(sheet => {
        // Barra superior de la hoja (agarradera + botón cerrar)
        const bar = document.createElement('div');
        bar.className = 'sheet-bar';
        bar.innerHTML = '<span class="sheet-grabber"></span>' +
            '<button type="button" class="sheet-close" aria-label="Cerrar"><i class="bi bi-x-lg"></i></button>';
        sheet.insertBefore(bar, sheet.firstChild);
        bar.querySelector('.sheet-close').addEventListener('click', close);

        const scope = sheet.closest('section') || document;

        // Botón flotante (+)
        scope.querySelectorAll('[data-sheet-open]').forEach(btn => {
            btn.addEventListener('click', () => open(sheet));
        });

        // Lápiz de editar: los otros scripts cargan los datos en el form, aquí solo se muestra
        scope.querySelectorAll('.btn-edit-trade, .btn-edit-dividend, .btn-edit-transaction').forEach(btn => {
            btn.addEventListener('click', () => open(sheet));
        });

        // Si el servidor devolvió errores de validación, mostrar el form de inmediato
        if (sheet.querySelector('.form-alert, .errorlist')) open(sheet);
    });

    backdrop.addEventListener('click', close);
    document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
    mq.addEventListener('change', e => { if (!e.matches) close(); });
})();
