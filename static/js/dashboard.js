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
                            console.log(value);
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

