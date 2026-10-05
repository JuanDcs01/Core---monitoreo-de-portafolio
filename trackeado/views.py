# views.py
from django.shortcuts import render, redirect, get_object_or_404
import yfinance as yf
from .models import Holding, UserHolding, WatchList, HoldingList
from .forms import WatchListForm
from pprint import pprint
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import humanize

@login_required
def index(request):

    user = request.user

    holdings = UserHolding.objects.select_related('holding').filter(user=user)

    print(holdings)

    if not holdings:
        return render(request, 'dashboard.html', {'holdings':holdings})

    symbols = [h.holding.symbol for h in holdings]

    data = yf.download(tickers=symbols, period="1d", interval="1m", prepost=True, group_by='ticker', threads=True)

    pprint(data.__dict__)

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

        if holdings_list:

            symbols = [h.holding.symbol for h in holdings_list]

            data = yf.download(tickers=symbols, period="1d", interval="1m", prepost=True, group_by='ticker', threads=True)

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

@login_required
def holding(request, symbol):

    holding = yf.Ticker(symbol)

    info = holding.info

    if info.get('longName'):

        df = holding.history(period="max")
        df_5d = holding.history(period="5d", interval="1h")
        df_1d = holding.history(period="1d", interval="5m", prepost=True)

        # 1. Reseteamos el índice para que la fecha pase a ser una columna normal
        df.reset_index(inplace=True)
        df_5d.reset_index(inplace=True)
        df_1d.reset_index(inplace=True)
        
        # 2. Formateamos la fecha a un string limpio ("YYYY-MM-DD")
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        df_5d["Datetime"] = df_5d["Datetime"].astype(str)
        df_1d["Datetime"] = df_1d["Datetime"].astype(str)

        history_list = df[['Date', 'Close']].to_dict(orient='records')
        history_list_5d = df_5d[['Datetime', 'Close']].to_dict(orient='records')
        history_list_1d = df_1d[['Datetime', 'Close']].to_dict(orient='records')

        context = {
            'symbol': symbol.upper(),
            'longName': info.get('longName'),
            'quoteType': info.get('quoteType'),
            'currentPrice': humanize.intcomma(info.get('currentPrice')) if info.get('currentPrice') else humanize.intcomma(info.get('regularMarketPrice')),
            'dayHigh':  humanize.intcomma(round(info.get('dayHigh'))) if info.get('dayHigh') else 0,
            'dayLow':  humanize.intcomma(round(info.get('dayLow'))) if info.get('dayLow') else 0,
            'dividendYield':  humanize.intcomma(info.get('dividendYield')),
            'fullExchangeName': info.get('fullExchangeName'),
            'fulldayChangeNumber': info.get('fulldayChange'),
            'fulldayChange': humanize.intcomma(round(info.get('fulldayChange'),2)) if info.get('fulldayChange') else 0,
            'fulldayChangePercent': humanize.intcomma(round(info.get('fulldayChangePercent'), 2)) if info.get('fulldayChangePercent') else 0,
            'industry': info.get('industry'),
            'marketCap': humanize.metric(info.get('marketCap')) if info.get('marketCap') else 0,
            'sector': info.get('sector'),
            'targetHighPrice': info.get('targetHighPrice'),
            'targetLowPrice': info.get('targetLowPrice'),
            'targetMeanPrice': info.get('targetMeanPrice'),
            'targetMedianPrice': info.get('targetMedianPrice'),
            'trailingPE': humanize.intcomma(round(info.get('trailingPE'), 2)) if info.get('trailingPE') else 0,
            'forwardPE': humanize.intcomma(round(info.get('forwardPE'), 2)) if info.get('forwardPE') else 0,
            'beta': humanize.intcomma(round(info.get('beta'), 2)) if info.get('beta') else 0,
            'marketState': info.get('marketState'),
            'fiftyTwoWeekHigh': humanize.intcomma(info.get('fiftyTwoWeekHigh')),
            'fiftyTwoWeekLow': humanize.intcomma(info.get('fiftyTwoWeekLow')),
            'recommendationKey': info.get('recommendationKey'),
            'history_list': history_list,
            'history_list_5d': history_list_5d,
            'history_list_1d': history_list_1d,
            '': info.get(''),
        }
    else:
        context = {}
    
    return render(request, 'holding.html', context)