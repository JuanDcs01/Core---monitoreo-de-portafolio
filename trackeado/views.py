# views.py
from django.shortcuts import render, redirect, get_object_or_404
import yfinance as yf
from .models import Holding, UserHolding, WatchList, HoldingList, WalletTransaction, Wallet
from .forms import WatchListForm, WalletTransactionForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import datetime
from django.conf import settings
from django.db import IntegrityError, transaction
from pprint import pprint
from decimal import Decimal

@login_required
def dashboard(request):

    user = request.user

    wallet = get_object_or_404(Wallet, user=user)

    balance = wallet.balance

    holdings = UserHolding.objects.select_related('holding').filter(user=user)

    watch_list = WatchList.objects.filter(user=user)

    if not holdings:
        return render(request, 'dashboard.html', {'holdings':holdings})

    symbols = [h.holding.symbol for h in holdings]

    holding = yf.Ticker('VOO')

    info = holding.info

    market_state = info.get('marketState')

    data = yf.download(tickers=symbols, start='2025-11-24', interval="1d", prepost=True, group_by='ticker', threads=True)
    data2 = yf.download(tickers=symbols, period='1d', interval='1m', prepost=True, group_by='ticker')

    for h in holdings:

        last_day_price = data.get(h.holding.symbol).get('Close').dropna().iloc[-2]
        current_price = data2.get(h.holding.symbol).get('Close').dropna().iloc[-1]
        h.day_change = round(current_price - last_day_price, 2)
        h.day_change_percent = round(h.day_change / current_price * 100, 2)

        h.price = round(current_price, 2)

        logo_symbol = h.holding.symbol.split('-')[0] if '-' in h.holding.symbol else h.holding.symbol
        h.logo_url = f'https://img.logo.dev/ticker/{logo_symbol}?token={settings.LOGODEV_TOKEN}&size=40'

    context = {
        'holdings': holdings,
        'market_state': market_state,
        'watch_list': watch_list,
        'balance': balance
    }

    return render(request, 'dashboard.html', {**context})


@login_required
def add_holding(request):

    user = request.user

    if request.method == 'POST':

        if not request.POST.get('symbol').upper():
            messages.error(request, 'Símbolo no encontrado')
            return redirect('dashboard')

        symbol = request.POST.get('symbol').upper()

        try:
            holding = Holding.objects.get(symbol=symbol)
        except:
            holding = None

        try:
            if holding:

                UserHolding.objects.create(user=user, holding=holding)
                messages.success(request, 'Símbolo agregado.')

            else: 

                ticker = yf.Ticker(symbol)     

                info = ticker.info

                if not info or ("regularMarketPrice" not in info and "longName" not in info and "shortName" not in info):
                    messages.success(request, 'Símbolo no encontrado.')
                    return redirect('dashboard')

                name = ticker.info.get('longName')
                type = ticker.info.get('quoteType')

                holding = Holding.objects.create(symbol=symbol, name=name, type=type)
                UserHolding.objects.create(user=user, holding=holding)
                messages.success(request, 'Símbolo agregado.')
            
        except IntegrityError:
            messages.error(request, 'El símbolo ya existe.')    

        return redirect('dashboard')


@login_required
def delete_holding(request):

    user_holding = get_object_or_404(UserHolding, id=request.POST.get('id'))

    if not user_holding:
        messages.error(request, 'Símbolo no encontrado')
        return redirect('dashboard')

    user_holding.delete()
    messages.success(request, 'Símbolo Eliminado de la cartera.')

    return redirect('holding', symbol=user_holding.holding.symbol)


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

    holding = yf.Ticker('VOO')

    info = holding.info

    market_state = info.get('marketState')

    if user.id == watch_list.user.id:

        holdings_list = HoldingList.objects.select_related('holding').filter(watch_list=watch_list)

        if holdings_list:

            symbols = [h.holding.symbol for h in holdings_list]

            data = yf.download(tickers=symbols, period="5d", interval="1d", prepost=True, group_by='ticker', threads=True)
            data2 = yf.download(tickers=symbols, period="1d", interval="1m", prepost=True, group_by='ticker', threads=True)

            for h in holdings_list:
                last_day_price = data.get(h.holding.symbol).get('Close').dropna().iloc[-2]
                current_price = round(data2.get(h.holding.symbol).get('Close').dropna().iloc[-1], 2)
                h.holding.day_change = round(current_price - last_day_price, 2)
                h.holding.day_change_percent = round(h.holding.day_change / current_price * 100, 2)

                h.holding.price = current_price

                logo_symbol = h.holding.symbol.split('-')[0] if '-' in h.holding.symbol else h.holding.symbol
                h.logo_url = f'https://img.logo.dev/ticker/{logo_symbol}?token={settings.LOGODEV_TOKEN}&size=40'
        
        return render(request, 'watch_list_details.html', {'holdings_list': holdings_list, 'watch_list': watch_list, 'market_state': market_state })

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

        try:
            if holding:

                HoldingList.objects.create(watch_list=watch_list, holding=holding)

            else: 

                ticker = yf.Ticker(symbol)     

                info = ticker.info

                if not info or ("regularMarketPrice" not in info and "longName" not in info and "shortName" not in info):
                    messages.success(request, 'Símbolo no encontrado.')
                    return redirect('dashboard')

                name = ticker.info.get('longName')
                type = ticker.info.get('quoteType')

                holding = Holding.objects.create(symbol=symbol, name=name, type=type)
                HoldingList.objects.create(watch_list=watch_list, holding=holding)

                messages.success(request, 'Símbolo agregado.')

        except IntegrityError:
                messages.error(request, 'El símbolo ya existe.')

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

    user = request.user

    holding = yf.Ticker(symbol)

    info = holding.info

    if not info.get('symbol'):
        messages.error(request, 'Símbolo no encontrado')
        return redirect('dashboard')

    h = Holding.objects.filter(symbol=symbol).first()

    exist = UserHolding.objects.filter(user=user, holding=h).first()

    ernings = holding.financials

    print(ernings.__dict__)

    if info.get('longName'):
        df = holding.history(period="max")
        df_5d = holding.history(period="5d", interval="15m", prepost=True)
        df_1d = holding.history(period="1d", interval="5m", prepost=True)

        # 1. Asegurar la zona horaria correcta (Nueva York) antes de extraer la hora
        # Prevenimos errores en caso de que yfinance devuelva fechas sin timezone (naive)
        for d in [df_5d, df_1d]:
            if d.index.tz is None:
                d.index = d.index.tz_localize('UTC').tz_convert('America/New_York')
            else:
                d.index = d.index.tz_convert('America/New_York')

        # 2. Función para clasificar la fase del mercado
        def get_market_phase(dt):
            t = dt.time()
            if t < datetime.time(9, 30):
                return 'pre'
            elif t >= datetime.time(16, 0):
                return 'post'
            else:
                return 'regular'

        # 3. Aplicar la función al índice de los dataframes intradía
        df_5d['Phase'] = df_5d.index.map(get_market_phase)
        df_1d['Phase'] = df_1d.index.map(get_market_phase)

        # 4. Reseteamos el índice
        df.reset_index(inplace=True)
        df_5d.reset_index(inplace=True)
        df_1d.reset_index(inplace=True)
        # 5. Formateamos las fechas a string
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        df_5d["Datetime"] = df_5d["Datetime"].astype(str)
        df_1d["Datetime"] = df_1d["Datetime"].astype(str)

        # 6. Convertimos a diccionarios, incluyendo 'Phase' en los de corto plazo
        history_list = df[['Date', 'Close']].to_dict(orient='records')
        history_list_5d = df_5d[['Datetime', 'Close', 'Phase']].to_dict(orient='records')
        history_list_1d = df_1d[['Datetime', 'Close', 'Phase']].to_dict(orient='records')

        for h in history_list_5d:
            h['Close'] = round(h['Close'], 2)
        for h in history_list_1d:
            h['Close'] = round(h['Close'], 2)
        for h in history_list:
            h['Close'] = round(h['Close'], 2)

        history_list[-1]['Close'] = history_list_1d[-1]['Close']
        history_list_5d[-1]['Close'] = history_list_1d[-1]['Close']

        logo_symbol = symbol.split('-')[0] if '-' in symbol else symbol

        context = {
            'symbol': symbol.upper(),
            'longName': info.get('longName'),
            'quoteType': info.get('quoteType'),
            'currentPrice': info.get('currentPrice') if info.get('currentPrice') else info.get('regularMarketPrice'),
            'postMarketPrice': round(info.get('postMarketPrice')) if info.get('postMarketPrice') else None,
            'dayHigh':  round(info.get('dayHigh')) if info.get('dayHigh') else 0,
            'dayLow':  round(info.get('dayLow')) if info.get('dayLow') else 0,
            'dividendYield':  info.get('dividendYield'),
            'fullExchangeName': info.get('fullExchangeName'),
            'fulldayChange': round(info.get('fulldayChange'),2) if info.get('fulldayChange') else 0,
            'fulldayChangePercent': round(info.get('fulldayChangePercent'), 2) if info.get('fulldayChangePercent') else 0,
            'postMarketChange': round(info.get('postMarketChange'), 2) if info.get('postMarketChange') else None,
            'postMarketChangePercent': round(info.get('postMarketChangePercent'), 2) if info.get('postMarketChangePercent') else None,
            'industry': info.get('industry'),
            'marketCap': info.get('marketCap') if info.get('marketCap') else 0,
            'sector': info.get('sector'),
            'targetHighPrice': info.get('targetHighPrice'),
            'targetLowPrice': info.get('targetLowPrice'),
            'targetMeanPrice': info.get('targetMeanPrice'),
            'targetMedianPrice': info.get('targetMedianPrice'),
            'trailingPE': round(info.get('trailingPE'), 2) if info.get('trailingPE') else 0,
            'forwardPE': round(info.get('forwardPE'), 2) if info.get('forwardPE') else 0,
            'beta': round(info.get('beta'), 2) if info.get('beta') else 0,
            'marketState': info.get('marketState'),
            'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh'),
            'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow'),
            'recommendationKey': info.get('recommendationKey'),
            'history_list': history_list,
            'history_list_5d': history_list_5d,
            'history_list_1d': history_list_1d,
            'logo_url': f"https://img.logo.dev/ticker/{logo_symbol}?token={settings.LOGODEV_TOKEN}&size=40",
            'exist': exist
        }
    else:
        context = {}
    
    return render(request, 'holding.html', context)

@login_required
def search_holding(request):

    symbol = request.POST.get('symbol').upper()

    if not symbol:
        messages.error(request, 'Símbolo no encontrado')
        return redirect('dashboard')    

    return redirect('holding', symbol)  

@login_required
def wallet_transactions(request):

    user = request.user

    wallet = get_object_or_404(Wallet, user=user)

    wallet_transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('date')

    balance = wallet.balance

    if request.method == 'GET':

        form = WalletTransactionForm()


    if request.method == 'POST':

        form = WalletTransactionForm(request.POST)

        if not form.is_valid():
            messages.error(request, 'No fue posible registrar la transación')
            return render(request, 'wallet_transactions.html', {'wallet_transactions': wallet_transactions, 'balance': balance, 'form': form,
                                                                'title': 'Registrar transación', 
                                                                'button': 'Registrar',})

        with transaction.atomic():
            wallet_transaction = form.instance
            wallet_transaction.wallet = wallet
            wallet_transaction.save()

            wallet.balance = wallet.balance + wallet_transaction.net_amount if wallet_transaction.type == 'D' else  wallet.balance - wallet_transaction.total
            wallet.commission_paid += wallet_transaction.commission
            wallet.save()

        messages.success(request, 'Transación regsitrada')
        return redirect('wallet_transactions')

    return render(request, 'wallet_transactions.html', {'wallet_transactions': wallet_transactions, 'balance': balance, 'form': form,
                                                        'title': 'Registrar transación', 
                                                        'button': 'Registrar',})

@login_required
def delete_wallet_transactions(request):

    user = request.user

    wallet = get_object_or_404(Wallet, user=user)

    wallet_transaction = get_object_or_404(WalletTransaction, id=request.POST.get('id'), wallet=wallet)

    with transaction.atomic():

        wallet_transaction.delete()
        wallet.balance = wallet.balance - wallet_transaction.net_amount if wallet_transaction.type == 'D' else  wallet.balance + wallet_transaction.total
        wallet.commission_paid -= wallet_transaction.commission
        wallet.save()

    messages.success(request, 'Transación eliminada.')

    return redirect('wallet_transactions')