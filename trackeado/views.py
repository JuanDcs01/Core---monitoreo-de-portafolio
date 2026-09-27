# views.py
import re

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET
import yfinance as yf

# BRK.B, BF-B, etc: letras/números + sufijo opcional de una letra tras punto o guion.
SYMBOL_RE = re.compile(r'^[A-Z0-9]{1,10}([.-][A-Z0-9]{1,3})?$')

# TTL del caché de cotizaciones extendidas. Debe ser <= al intervalo de
# polling del frontend (20s) para no servir datos más viejos de lo que el
# usuario ya está pidiendo, pero suficientemente alto para que, con varios
# usuarios mirando los mismos símbolos, la mayoría de los requests se
# resuelvan desde caché en vez de pegarle a yfinance (que hace scraping y
# es la parte lenta y frágil del pipeline).
QUOTE_CACHE_TTL_SECONDS = 15


def stock_dashboard(request):
    context = {
        'dashboard_config': {
            'finnhub_api_key': settings.FINNHUB_API_KEY,
        },
    }
    return render(request, 'dashboard.html', context)


def _fetch_quote_from_yfinance(symbol):
    """
    Pega contra yfinance (scraping, no es una API oficial) y arma el dict
    de respuesta. Separado de la view para que el cacheo de abajo sea claro
    y testeable.
    """
    ticker = yf.Ticker(symbol)
    info = ticker.info or {}

    market_state = info.get('marketState', 'UNKNOWN')
    # marketState típicamente es: PRE, REGULAR, POST, CLOSED, POSTPOST, PREPRE

    return {
        'symbol': symbol,
        'marketState': market_state,
        'regularMarketPrice': info.get('regularMarketPrice'),
        'preMarketPrice': info.get('preMarketPrice'),
        'preMarketChangePercent': info.get('preMarketChangePercent'),
        'postMarketPrice': info.get('postMarketPrice'),
        'postMarketChangePercent': info.get('postMarketChangePercent'),
    }


@require_GET
def stock_quote(request, symbol):
    """
    Devuelve el precio actual de un símbolo vía yfinance, incluyendo
    precio de pre-market / after-hours cuando el mercado regular está cerrado.

    yfinance no es una API oficial de Yahoo Finance (hace scraping), así que
    puede fallar o cambiar de formato sin aviso. No usar como fuente única
    para nada crítico.

    Cachea la respuesta por símbolo (ver QUOTE_CACHE_TTL_SECONDS): sin esto,
    cada usuario con el dashboard abierto dispara su propio scraping cada
    20s por cada símbolo que agregó, lo cual no escala (N usuarios x M
    símbolos requests concurrentes a yfinance) y es la forma más fácil de
    terminar bloqueado/rate-limiteado por Yahoo. Con el caché compartido,
    N usuarios mirando el mismo símbolo generan como máximo 1 request real
    cada QUOTE_CACHE_TTL_SECONDS.
    """
    symbol = symbol.strip().upper()
    if not SYMBOL_RE.match(symbol):
        return JsonResponse({'error': 'Símbolo inválido.'}, status=400)

    cache_key = f'stock_quote:{symbol}'
    data = cache.get(cache_key)

    if data is None:
        try:
            data = _fetch_quote_from_yfinance(symbol)
        except Exception as exc:
            return JsonResponse(
                {'error': f'No se pudo obtener datos de {symbol}: {exc}'},
                status=502,
            )
        cache.set(cache_key, data, QUOTE_CACHE_TTL_SECONDS)

    return JsonResponse(data)
