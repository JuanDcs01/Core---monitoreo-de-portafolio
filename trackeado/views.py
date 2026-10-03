# views.py
from django.shortcuts import render, redirect, get_object_or_404
import yfinance as yf
from .models import Holdings
from pprint import pprint
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
def index(request):

    holdings = Holdings.objects.all()

    print(holdings)

    if not holdings:
        return render(request, 'dashboard.html', {'holdings':holdings})

    symbols = [holding.symbol for holding in holdings]

    data = yf.download(symbols, period="1d", group_by="ticker")

    print(data)

    for holding in holdings:
        
        holding.price = round(data.get(holding.symbol).get('Open').dropna().iloc[-1], 2)

    context = {
        'holdings': holdings
    }

    return render(request, 'dashboard.html', {**context})

def add_holding(request):

    if request.method == 'POST':

        symbol = request.POST.get('symbol').upper()

        ticker = yf.Ticker(symbol)     

        info = ticker.info

        if not info or ("regularMarketPrice" not in info and "longName" not in info and "shortName" not in info):
            messages.success(request, 'Símbolo no encontrado.')
            return redirect('index')

        name = ticker.info.get('longName')
        type = ticker.info.get('quoteType')

        Holdings.objects.create(symbol=symbol, name=name, type=type)

        messages.success(request, 'Símbolo agregado.')
        return redirect('index')

def delete_holding(request):

    holding = get_object_or_404(Holdings, id=request.POST.get('id'))

    holding.delete()
    messages.success(request, 'Símbolo Eliminado.')

    return redirect('index')