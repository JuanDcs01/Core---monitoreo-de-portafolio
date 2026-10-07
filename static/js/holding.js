    const historyDataMax = JSON.parse(document.getElementById('history-max').textContent);
    const historyData5d = JSON.parse(document.getElementById('history-5d').textContent);
    const historyData1d = JSON.parse(document.getElementById('history-1d').textContent);

    let miGrafico = null;
    let currentRawData = []; 
    // NUEVAS VARIABLES GLOBALES PARA CONTROLAR EL COLOR EN LOS CALLBACKS
    let isLinePositive = true; 
    let currentLineColor = 'rgb(0, 128, 0)';

    // Función para actualizar los valores de texto en la pantalla
    function actualizarTextos(primerPrecio, ultimoPrecio, isPositive, colorHex) {
        const diferencia = ultimoPrecio - primerPrecio;
        const porcentaje = (diferencia / primerPrecio) * 100;
        
        const numberSpan = document.getElementById('numberChange');
        const percentSpan = document.getElementById('percentChange');
        const priceSpan = document.getElementById('currentPrice');
        
        if (numberSpan && percentSpan && priceSpan) {
            numberSpan.innerText = isPositive ? `(+${precioFormateado(diferencia)})` : `(${precioFormateado(diferencia)})`;
            percentSpan.innerText = `${precioFormateado(porcentaje)}%`;
            priceSpan.innerText = ultimoPrecio;
            numberSpan.style.color = colorHex;
            percentSpan.style.color = colorHex;
        }
    }

    // Inicializador del gráfico
    function initChart(canvasId, dataset, maxTicksLimit, tension) {
        const ctx = document.getElementById(canvasId);
        currentRawData = dataset;

        const key = dataset[0] && dataset[0]['Datetime'] ? 'Datetime' : 'Date';
        const labels = dataset.map(item => item[key]);
        const prices = dataset.map(item => item['Close']);
        
        const primerPrecio = prices[0];
        const ultimoPrecio = prices[prices.length - 1];
        
        // ACTUALIZAMOS LAS VARIABLES GLOBALES
        isLinePositive = (ultimoPrecio - primerPrecio) >= 0;
        currentLineColor = isLinePositive ? 'rgb(0, 128, 0)' : 'rgb(210, 4, 45)';

        miGrafico = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    fill: true,
                    backgroundColor: (context) => {
                        const chart = context.chart;
                        const { ctx, chartArea } = chart;
                        if (!chartArea) return null;
                        
                        const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                        
                        // USA LA VARIABLE GLOBAL isLinePositive
                        if (isLinePositive) {
                            gradient.addColorStop(0, 'rgba(0, 128, 0, 0.4)');
                            gradient.addColorStop(1, 'rgba(0, 128, 0, 0.0)');
                        } else {
                            gradient.addColorStop(0, 'rgba(210, 4, 45, 0.4)');
                            gradient.addColorStop(1, 'rgba(210, 4, 45, 0.0)');
                        }
                        return gradient;
                    },
                    data: prices,
                    borderColor: currentLineColor,
                    tension: tension,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    pointHoverBackgroundColor: 'white',
                    pointHoverBorderColor: currentLineColor,
                    pointHoverBorderWidth: 2,
                    
                    segment: {
                        borderDash: ctx => {
                            const rawItem = currentRawData[ctx.p0DataIndex]; 
                            if (rawItem && rawItem.Phase && rawItem.Phase !== 'regular') {
                                return [5, 5]; 
                            }
                            return undefined; 
                        },
                        borderColor: ctx => {
                            const rawItem = currentRawData[ctx.p0DataIndex]; 
                            if (rawItem && rawItem.Phase && rawItem.Phase !== 'regular') {
                                // USA LA VARIABLE GLOBAL currentLineColor
                                return currentLineColor.replace('rgb', 'rgba').replace(')', ', 0.4)');
                            }
                            return currentLineColor; 
                        }
                    }
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: 2000,
                interaction: { mode: 'index', intersect: false },
                plugins: { legend: { 
                    display: false 
                    },tooltip: {
                        callbacks: {
                            label: function(context) {
                                let valor = context.parsed.y;
                                return `Precio: $${precioFormateado(valor)}`;
                            }, title: function(tooltipItems) {
                                let item = tooltipItems[0]['label'];
                                date = new Date(item.replace(' ', 'T'))

                                return date.toLocaleString('es-ES', {
                                            weekday: 'short',
                                            year: 'numeric',
                                            month: 'short',
                                            day: '2-digit',
                                            hour: 'numeric',
                                            minute: '2-digit',
                                            hour12: true // o false para 24h
                                        });
                            }
                        }
                    } },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: {
                            autoSkip: true,
                            maxTicksLimit: maxTicksLimit,
                            callback: function(value) {
                                const date = this.getLabelForValue(value);
                                if (!date) return '';
                                if (date.length > 11) return new Date(date).toLocaleDateString('es-DO', { hour: 'numeric', minute: '2-digit', hour12: true }).slice(10); 
                                else return new Date(date).toLocaleDateString('es-DO', { day: '2-digit', month: 'short' });
                            }
                        }
                    },
                    y: {
                        beginAtZero: false, 
                        ticks: { padding: 10 }
                    }
                }
            }
        });
        
        actualizarTextos(primerPrecio, ultimoPrecio, isLinePositive, currentLineColor);
    }

    // Actualizador eficiente (sin destruir el gráfico)
    function actualizarGrafico(historyData, maxTicksLimit, period = null, tension = 0.1) {
    let dataset = historyData;
    const ultimoElemento = historyData.at(-1);
    const fechaUltimoStr = ultimoElemento['Date'] || ultimoElemento['Datetime'];
    const fechaUltima = new Date(fechaUltimoStr.replace(' ', 'T'));

    if (period && period !== 'Yyd') {
        let fechaInicio = new Date(fechaUltima);

        // Dependiendo del período, restamos el tiempo correspondiente
        if (period === '1D') {
            fechaInicio.setDate(fechaUltima.getDate() - 1);
        } else if (period === '5D') {
            fechaInicio.setDate(fechaUltima.getDate() - 5);
        } else if (period === '1M') {
            fechaInicio.setMonth(fechaUltima.getMonth() - 1);
        } else if (period === '3M') {
            fechaInicio.setMonth(fechaUltima.getMonth() - 3);
        } else if (period === '6M') {
            fechaInicio.setMonth(fechaUltima.getMonth() - 6);
        } else if (period === '1Y') {
            fechaInicio.setFullYear(fechaUltima.getFullYear() - 1);
        } else if (period === '5Y') {
            fechaInicio.setFullYear(fechaUltima.getFullYear() - 5);
        }

        // Filtramos los datos que sean mayores o iguales a la fecha de inicio calculada
        dataset = historyData.filter(item => {
            const itemDateStr = item['Date'] || item['Datetime'];
            return new Date(itemDateStr.replace(' ', 'T')) >= fechaInicio;
        });
    }

    if (period === 'YTD') {
        const currentYear = fechaUltimoStr.slice(0, 4);
        dataset = historyData.filter(item => {
            const itemDateStr = item['Date'] || item['Datetime'];
            return itemDateStr.slice(0, 4) === currentYear;
        });
    }

    currentRawData = dataset; 

    const key = dataset[0] && dataset[0]['Datetime'] ? 'Datetime' : 'Date';
    const labels = dataset.map(item => item[key]);
    const prices = dataset.map(item => item['Close']);
    
    const primerPrecio = prices[0];
    const ultimoPrecio = prices[prices.length - 1];
    
    isLinePositive = (ultimoPrecio - primerPrecio) >= 0;
    currentLineColor = isLinePositive ? 'rgb(0, 128, 0)' : 'rgb(210, 4, 45)';

    miGrafico.data.labels = labels;
    miGrafico.data.datasets[0].data = prices;
    miGrafico.data.datasets[0].borderColor = currentLineColor;
    miGrafico.data.datasets[0].pointHoverBorderColor = currentLineColor;
    miGrafico.data.datasets[0].tension = tension;
    miGrafico.options.animation.duration = 2000;
    
    miGrafico.update();
    actualizarTextos(primerPrecio, ultimoPrecio, isLinePositive, currentLineColor);
}

    // Ejecutar inicialización 
    initChart("history", historyData1d, 8, 0.2);

    // Event Listeners 
const botones = document.querySelectorAll('.period');
botones.forEach(button => {
    button.addEventListener('click', function() {
        botones.forEach(b => b.classList.remove('active-period'));
        this.classList.add('active-period');

        const id = this.id;
        if (id === 'year1') actualizarGrafico(historyDataMax, 7, '1Y');
        else if (id === 'year5') actualizarGrafico(historyDataMax, 7, '5Y');
        else if (id === 'months6') actualizarGrafico(historyDataMax, 7, '6M');
        else if (id === 'months3') actualizarGrafico(historyDataMax, 7, '3M', 0.2);
        else if (id === 'months1') actualizarGrafico(historyDataMax, 7, '1M', 0.2);
        else if (id === 'days5') actualizarGrafico(historyData5d, 8, '5D', 0.2);
        else if (id === 'days1') actualizarGrafico(historyData1d, 8, '1D', 0.2);
        else if (id === 'YTD') actualizarGrafico(historyDataMax, 7, 'YTD');
        else if (id === 'max') actualizarGrafico(historyDataMax, 7, null);
    });
});

    function precioFormateado(number) {

        return number.toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
        })
    };

    document.getElementById('days1').click();