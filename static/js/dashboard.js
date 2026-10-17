/************************************
Gráfiico de distribución por tipo
************************************/
const type_distribution_data = JSON.parse(
    document.getElementById("type-distribution-data").textContent
);

const labels = Object.keys(type_distribution_data);
const values = Object.values(type_distribution_data);

// colores a utilizar en la grafica
const colors = [
    "#A2D2FF",
    "#FFCFD2",
    "#B9FBC0",
];

// obtener elemento canvas
const ctx = document.getElementById('type-distribution');

// objeto literal de los datos
const data = {
    labels: labels,
    datasets: [
      {
        label: 'Dataset 1',
        data: values,
        backgroundColor: colors,
        borderColor: "#f4f4f4",
        hoverBackgroundColor: "#9b9b9b"
      }
    ]
  };

// construccion de la grafica
const distributionChart = new Chart(ctx, {
  type: 'doughnut',
  data: data,
  options: {
    responsive: false,
    plugins: {
      legend: {
        display: false,
      },
      // Configuración del plugin de etiquetas
      datalabels: {
        color: '#000000', // Color del texto (blanco para que resalte)
        font: {
          weight: 'bold',
          size: 14
        },
        formatter: function(value, context) {
          // Muestra el valor seguido del signo de porcentaje
          if (value == 0) {
            return ''
          } else {
            return value + '%';
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
  // ¡Importante! Registra el plugin aquí para que se active
  plugins: [ChartDataLabels] 
});