# views.py
from django.shortcuts import render, redirect, get_object_or_404
import yfinance as yf
from .models import Holding, UserHolding, WatchList, HoldingList
from .forms import WatchListForm
from pprint import pprint
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
def index(request):

    user = request.user

    holdings = UserHolding.objects.select_related('holding').filter(user=user)

    print(holdings)

    if not holdings:
        return render(request, 'dashboard.html', {'holdings':holdings})

    symbols = [h.holding.symbol for h in holdings]

    data = yf.download(symbols, period="1d", group_by="ticker")

    for h in holdings:
        
        h.price = round(data.get(h.holding.symbol).get('Open').dropna().iloc[-1], 2)

    context = {
        'holdings': holdings
    }

    return render(request, 'dashboard.html', {**context})


@login_required
def add_holding(request):

    user = request.user

    if request.method == 'POST':

        symbol = request.POST.get('symbol').upper()

        try:
            holding = Holding.objects.get(symbol=symbol)
        except:
            holding = None

        if holding:

            UserHolding.objects.create(user=user, holding=holding)

        else: 

            ticker = yf.Ticker(symbol)     

            info = ticker.info

            if not info or ("regularMarketPrice" not in info and "longName" not in info and "shortName" not in info):
                messages.success(request, 'Símbolo no encontrado.')
                return redirect('index')

            name = ticker.info.get('longName')
            type = ticker.info.get('quoteType')

            holding = Holding.objects.create(symbol=symbol, name=name, type=type)
            UserHolding.objects.create(user=user, holding=holding)

        messages.success(request, 'Símbolo agregado.')
        return redirect('index')


@login_required
def delete_holding(request):

    holding = get_object_or_404(UserHolding, id=request.POST.get('id'))

    holding.delete()
    messages.success(request, 'Símbolo Eliminado.')

    return redirect('index')


@login_required
def watch_lists(request):

    user = request.user

    watch_lists = WatchList.objects.filter(user=user)

    if request.method == 'GET':

        form = WatchListForm()

    if request.method == 'POST':

        form = WatchListForm(request.POST)

        if not form.is_valid():
            messages.error(request, 'No fue posible realizar la acción.')
            return render(request, 'create_watch_list.html', {'form': form, 'title': 'Crear lista', 'button': 'Crear', 'watch_lists': watch_lists })

        watch_list = form.instance
        watch_list.user = user
        watch_list.save()

        messages.success(request, 'Lista creada.')
        return redirect('watch_lists')    

    return render(request, 'watch_lists.html', {'form': form, 'title': 'Crear lista', 'button': 'Crear', 'watch_lists': watch_lists })


@login_required
def watch_list_details(request, watch_list):

    user = request.user

    watch_list = get_object_or_404(WatchList, name=watch_list)

    if user.id == watch_list.user.id:

        holdings_list = HoldingList.objects.select_related('holding').filter(watch_list=watch_list)

        symbols = [h.holding.symbol for h in holdings_list]

        data = yf.download(symbols, period="1d", group_by="ticker")

        for h in holdings_list:
            h.holding.price = round(data.get(h.holding.symbol).get('Open').dropna().iloc[-1], 2)
        
        return render(request, 'watch_list_details.html', {'holdings_list': holdings_list, 'watch_list': watch_list })

    else:
        return redirect('watch_lists')  


@login_required
def add_holding_list(request):

    if request.method == 'POST':

        symbol = request.POST.get('symbol').upper()
        watch_list_id = request.POST.get('watch_list_id')

        watch_list = get_object_or_404(WatchList, id=watch_list_id)

        try:
            holding = Holding.objects.get(symbol=symbol)
        except:
            holding = None

        if holding:

            HoldingList.objects.create(watch_list=watch_list, holding=holding)

        else: 

            ticker = yf.Ticker(symbol)     

            info = ticker.info

            if not info or ("regularMarketPrice" not in info and "longName" not in info and "shortName" not in info):
                messages.success(request, 'Símbolo no encontrado.')
                return redirect('index')

            name = ticker.info.get('longName')
            type = ticker.info.get('quoteType')

            holding = Holding.objects.create(symbol=symbol, name=name, type=type)
            HoldingList.objects.create(watch_list=watch_list, holding=holding)

        messages.success(request, 'Símbolo agregado.')
        return redirect('watch_list_details', watch_list.name)

    return render(request, 'watch_list_details.html', {})


@login_required
def delete_holding_list(request):

    if request.method == 'POST':

        holding_list_id = request.POST.get('holding_list_id')
        watch_list = request.POST.get('watch_list')

        holding_list = get_object_or_404(HoldingList, id=holding_list_id)
        holding_list.delete()

        messages.success(request, 'Eliminado de la lista.')
        return redirect('watch_list_details', watch_list)


@login_required
def delete_watch_lists(request):

    if request.method == 'POST':

        watch_list_id = request.POST.get('watch_list_id')        

        watch_list = get_object_or_404(WatchList, id=watch_list_id)
        watch_list.delete()

        messages.success(request, 'Lista eliminada.')
        return redirect('watch_lists')