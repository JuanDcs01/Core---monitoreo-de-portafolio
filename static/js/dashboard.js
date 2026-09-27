// dashboard.js
// Lógica del panel financiero en tiempo real (Finnhub + yfinance backend).

document.addEventListener('DOMContentLoaded', function () {
    // El token viaja como JSON embebido en el HTML (via {% json_script %}),
    // no como texto interpolado directamente en el JS: así Django lo escapa
    // correctamente y este archivo se puede servir como estático puro,
    // cacheable por el navegador/CDN sin volver a generarlo por request.
    const config = JSON.parse(document.getElementById('dashboard-config').textContent);
    const finnhubToken = config.finnhub_api_key;

    const socket = new WebSocket(`wss://ws.finnhub.io?token=${finnhubToken}`);

    let isSocketOpen = false;
    const subscribedSymbols = new Set();
    const pendingSymbols = [];

    // Símbolo válido: letras/números y opcionalmente un sufijo tipo ".B" o "-B"
    // (ej. BRK.B, BF-B). La validación real y autoritativa vive en el backend.
    const SYMBOL_RE = /^[A-Z0-9]{1,10}([.-][A-Z0-9]{1,3})?$/;

    function createCard(symbol) {
        const col = document.createElement('div');
        col.className = 'col-md-4 mb-3';
        col.id = `card-${symbol}`;
        col.innerHTML = `
            <div class="card shadow-sm">
                <div class="card-body">
                    <h5 class="card-title">${symbol}</h5>
                    <h3 class="text-success" id="price-${symbol}">Cargando...</h3>
                    <div class="small text-muted" id="extended-${symbol}"></div>
                </div>
            </div>
        `;
        document.getElementById('stock-container').appendChild(col);
    }

    // --- Pre-market / after-hours vía yfinance (backend Django) ---

    const EXTENDED_POLL_MS = 20000; // yfinance hace scraping, no abusar del polling

    async function fetchExtendedQuote(symbol) {
        const extEl = document.getElementById(`extended-${symbol}`);
        try {
            const resp = await fetch(`/api/quote/${symbol}/`);
            if (!resp.ok) {
                let detail = resp.statusText;
                try {
                    const errBody = await resp.json();
                    if (errBody.error) detail = errBody.error;
                } catch (_) { /* la respuesta no era JSON */ }
                console.error(`Error obteniendo cotización de ${symbol} (HTTP ${resp.status}):`, detail);
                if (extEl) extEl.innerText = `Error: ${detail}`;
                return;
            }
            const data = await resp.json();
            updateExtendedDisplay(symbol, data);
        } catch (err) {
            console.error(`No se pudo obtener cotización extendida de ${symbol}:`, err);
            if (extEl) extEl.innerText = 'Error de red al pedir la cotización.';
        }
    }

    function updateExtendedDisplay(symbol, data) {
        const priceEl = document.getElementById(`price-${symbol}`);
        const extEl = document.getElementById(`extended-${symbol}`);
        if (!priceEl || !extEl) return;

        const state = data.marketState;
        const isRegularOpen = state === 'REGULAR';

        // Mercado regular abierto: el WebSocket de Finnhub manda los trades en vivo,
        // así que no pisamos ese precio, solo limpiamos la etiqueta de extendido.
        if (isRegularOpen) {
            extEl.innerText = '';
            return;
        }

        // Solo hay 3 escenarios: horario regular (ya cubierto arriba), pre-market,
        // y post-market (esto último cubre todo lo demás: after-hours, cerrado, fin de semana, etc.)
        let label = null;
        let price = null;

        if (state === 'PRE' && data.preMarketPrice != null) {
            label = 'Pre-market';
            price = data.preMarketPrice;
        } else if (data.postMarketPrice != null) {
            label = 'After-hours';
            price = data.postMarketPrice;
        } else if (data.regularMarketPrice != null) {
            // Fallback por si yfinance no trae postMarketPrice (pasa seguido en fines de semana)
            label = 'Último cierre';
            price = data.regularMarketPrice;
        }

        if (price != null) {
            // Si todavía dice "Cargando..." (no llegó ningún trade por WebSocket), lo llenamos.
            if (priceEl.innerText === 'Cargando...') {
                priceEl.innerText = `$${price.toFixed(2)}`;
            }
            extEl.innerText = `${label}: $${price.toFixed(2)}`;
        } else {
            // yfinance respondió pero sin ninguno de los campos de precio que esperamos.
            console.warn(`Respuesta de ${symbol} sin precio utilizable:`, data);
            extEl.innerText = `(sin datos: marketState=${state ?? 'desconocido'})`;
        }
    }

    function pollExtendedQuotes() {
        subscribedSymbols.forEach(symbol => fetchExtendedQuote(symbol));
    }

    setInterval(pollExtendedQuotes, EXTENDED_POLL_MS);

    function sendSubscribe(symbols) {
        // El protocolo de Finnhub suscribe un símbolo por mensaje.
        symbols.forEach(symbol => {
            socket.send(JSON.stringify({ type: 'subscribe', symbol: symbol }));
        });
    }

    function subscribeSymbol(symbol) {
        symbol = symbol.trim().toUpperCase();
        if (!symbol) return;

        if (subscribedSymbols.has(symbol)) {
            showError(`${symbol} ya está en la lista.`);
            return;
        }

        if (!SYMBOL_RE.test(symbol)) {
            showError(`"${symbol}" no parece un símbolo válido.`);
            return;
        }

        if (subscribedSymbols.size >= 30) {
            // Cada símbolo suma: una suscripción de WebSocket + un polling propio
            // cada 20s contra el backend. Sin este tope, un usuario podría agregar
            // cientos de símbolos y degradar el rendimiento de su propia pestaña
            // (y la carga sobre el backend/yfinance) sin límite.
            showError('Máximo 30 símbolos por sesión.');
            return;
        }

        clearError();
        subscribedSymbols.add(symbol);
        createCard(symbol);
        fetchExtendedQuote(symbol);

        if (isSocketOpen) {
            sendSubscribe([symbol]);
        } else {
            // Se suscribe apenas abra la conexión
            pendingSymbols.push(symbol);
        }
    }

    function showError(msg) {
        document.getElementById('symbol-error').innerText = msg;
    }

    function clearError() {
        document.getElementById('symbol-error').innerText = '';
    }

    // Listeners del buscador
    document.getElementById('add-symbol-btn').addEventListener('click', function () {
        const input = document.getElementById('symbol-input');
        subscribeSymbol(input.value);
        input.value = '';
    });

    document.getElementById('symbol-input').addEventListener('keydown', function (event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            document.getElementById('add-symbol-btn').click();
        }
    });

    socket.addEventListener('open', function () {
        console.log('Conectado al WebSocket de Finnhub.');
        isSocketOpen = true;

        // Símbolos iniciales + cualquiera agregado antes de que abriera la conexión
        subscribeSymbol('AAPL');
        subscribeSymbol('NVDA');
        if (pendingSymbols.length > 0) {
            sendSubscribe(pendingSymbols.splice(0));
        }
    });

    socket.addEventListener('message', function (event) {
        const msg = JSON.parse(event.data);

        // Finnhub manda pings periódicos para mantener viva la conexión; se ignoran.
        if (msg.type === 'ping') return;

        if (msg.type === 'error') {
            console.error('Error de Finnhub:', msg.msg);
            showError(`Error de Finnhub: ${msg.msg}`);
            return;
        }

        // Trades en tiempo real: { type: 'trade', data: [{ s, p, t, v }, ...] }
        if (msg.type === 'trade' && Array.isArray(msg.data)) {
            msg.data.forEach(trade => {
                const symbol = trade.s;  // Símbolo
                const price = trade.p;   // Precio del trade

                const priceElement = document.getElementById(`price-${symbol}`);
                if (priceElement && typeof price === 'number') {
                    priceElement.innerText = `$${price.toFixed(2)}`;
                }
            });
        }
    });

    socket.addEventListener('error', function (error) {
        console.error('Error en el WebSocket:', error);
    });

    socket.addEventListener('close', function () {
        console.log('Conexión WebSocket cerrada.');
    });
});
