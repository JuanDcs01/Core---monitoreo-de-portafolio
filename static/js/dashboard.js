/************************************
Gráfiico de distribución por tipo
************************************/
// Función para crear gráficos de dona (doughnut) de manera reutilizable
function createDoughnutChart(canvasId, dataElementId, chartLabel = 'Dataset 1') {
    // 1. Obtener y parsear los datos desde el DOM
    const dataElement = document.getElementById(dataElementId);
    if (!dataElement) return null; // Validación por si no existe el elemento
    
    const chartData = JSON.parse(dataElement.textContent);
    const labels = Object.keys(chartData);
    const values = Object.values(chartData);

    // 2. Colores a utilizar en la gráfica
    const colors = [
        "#A2D2FF", "#B9FBC0", "#FEFAE0", "#FFCFD2", 
        "#E1DBFF", "#FDE4CF", "#CFFAF1", "#F1F1F1", 
        "#C8E6C9", "#FFE0B2", "#E3F2FD", "#FCE4EC"
    ];

    // 3. Obtener elemento canvas
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    // 4. Configuración de los datos
    const data = {
        labels: labels,
        datasets: [{
            label: chartLabel,
            data: values,
            backgroundColor: colors,
            borderColor: "#f4f4f4",
            hoverBackgroundColor: "#9b9b9b"
        }]
    };

    // 5. Construcción y retorno de la gráfica
    return new Chart(ctx, {
        type: 'doughnut',
        data: data,
        options: {
            responsive: false,
            plugins: {
                legend: {
                    display: false,
                },
                datalabels: {
                    color: '#000000',
                    font: {
                        weight: 'bold',
                        size: 14
                    },
                    formatter: function(value) {

                        if (value > 5) {
                            return value == 0 ? '' : value + '%';
                        } else {
                            return ''
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.raw}%`;
                        }
                    }
                }
            }
        },
        plugins: [ChartDataLabels]
    });
}

// Gráfica de distribución por tipo
const typeDistributionChart = createDoughnutChart(
    'type-distribution', 
    'type-distribution-data', 
    'Tipos'
);

// Gráfica de distribución por holding (Reutilizando la misma lógica)
const holdingDistributionChart = createDoughnutChart(
    'holding-distribution', // Asegúrate de tener un <canvas id="holding-distribution"></canvas> en tu HTML
    'holding-distribution-data', 
    'Holdings'
);

// Gráfica de distribución por riesgo
const riskDistributionChart = createDoughnutChart(
    'risk-distribution',
    'risk-distribution-data', 
    'Risks'
);

document.addEventListener('DOMContentLoaded', () => {
    const dropdown = document.getElementById('holdings-filter');
    const toggleBtn = document.getElementById('filter-toggle');
    const menu = document.getElementById('filter-menu');
    const sortList = document.getElementById('sort-holdings');
    const sharesCheck = document.getElementById('filter-with-shares');
    const tableBody = document.querySelector('.portfolio-table tbody');
    const emptyRow = document.getElementById('holdings-filter-empty');

    if (!dropdown || !toggleBtn || !menu || !sortList || !sharesCheck || !tableBody) return;

    /* ---------- Abrir / cerrar el menú ---------- */
    const setOpen = (open) => {
        menu.classList.toggle('is-open', open);
        toggleBtn.setAttribute('aria-expanded', String(open));
    };

    toggleBtn.addEventListener('click', () => {
        setOpen(!menu.classList.contains('is-open'));
    });

    // Cerrar al hacer clic fuera del menú
    document.addEventListener('click', (e) => {
        if (!dropdown.contains(e.target)) setOpen(false);
    });

    // En móvil el menú es una hoja inferior con fondo oscuro: un toque fuera solo la cierra
    // (en fase de captura, para que no active el enlace de la fila que quedó debajo)
    const mobileMq = window.matchMedia('(max-width: 767.98px)');
    document.addEventListener('click', (e) => {
        if (mobileMq.matches && menu.classList.contains('is-open') && !dropdown.contains(e.target)) {
            e.preventDefault();
            e.stopPropagation();
            setOpen(false);
        }
    }, true);

    // Cerrar con Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && menu.classList.contains('is-open')) {
            setOpen(false);
            toggleBtn.focus();
        }
    });

    /* ---------- Filtrar y ordenar ---------- */
    const getSortValue = () => {
        const active = sortList.querySelector('.filter-option.is-active');
        return active ? active.dataset.sort : '';
    };

    const applyFilters = () => {
        const rows = Array.from(tableBody.querySelectorAll('.holding-row'));

        // 1. Filtro: solo activos con acciones actualmente
        const onlyWithShares = sharesCheck.checked;
        let visibleCount = 0;
        rows.forEach(row => {
            const shares = parseFloat(row.getAttribute('data-shares')) || 0;
            const hide = onlyWithShares && shares <= 0;
            row.classList.toggle('is-hidden', hide);
            if (!hide) visibleCount++;
        });

        if (emptyRow) emptyRow.classList.toggle('is-hidden', visibleCount > 0);

        // 2. Orden
        const selectedValue = getSortValue();
        if (!selectedValue) return;

        const separatorIndex = selectedValue.lastIndexOf('_');
        const field = selectedValue.substring(0, separatorIndex);
        const direction = selectedValue.substring(separatorIndex + 1);

        rows.sort((rowA, rowB) => {
            const valA = parseFloat(rowA.getAttribute(`data-${field}`)) || 0;
            const valB = parseFloat(rowB.getAttribute(`data-${field}`)) || 0;
            return direction === 'asc' ? valA - valB : valB - valA;
        });

        rows.forEach(row => tableBody.appendChild(row));
    };

    /* ---------- Eventos ---------- */
    sortList.addEventListener('click', (e) => {
        const option = e.target.closest('.filter-option');
        if (!option) return;

        sortList.querySelectorAll('.filter-option').forEach(btn => {
            const isSelected = btn === option;
            btn.classList.toggle('is-active', isSelected);
            btn.setAttribute('aria-selected', String(isSelected));
        });
        applyFilters();
    });

    sharesCheck.addEventListener('change', applyFilters);

    // Estado inicial: checkbox marcado + orden por defecto
    applyFilters();
});