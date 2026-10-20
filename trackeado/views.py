# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
import yfinance as yf
from .models import Holding, UserHolding, WatchList, HoldingList, WalletTransaction, Wallet, Trade, Dividend
from .forms import WatchListForm, WalletTransactionForm, TradeForm, DividendForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import datetime
from django.conf import settings
from django.db import IntegrityError, transaction, connection, reset_queries
from pprint import pprint
from decimal import Decimal
from datetime import date, timedelta
from django.db.models import Sum

# Opción 1: Directa desde Dividend (la más eficiente y legible)
resultado = (
    Dividend.objects
    .filter(reinvested=False)
    .values('user_holding_id', 'user_holding__holding__symbol')
    .annotate(total_net_amount=Sum('net_amount'))
    .values('user_holding__holding__symbol', 'total_net_amount')
)

###############################
# Inicio 
###############################
@login_required
def dashboard(request):

    #todo: obtener datos a utilizar

    user = request.user
    wallet = get_object_or_404(Wallet, user=user)
    user_holdings = UserHolding.objects.select_related('holding').filter(user=user)
    trades = list(Trade.objects.select_related('user_holding__holding').filter(user=user).order_by('date', 'id'))
    dividends = dict(Dividend.objects.filter(reinvested=False).values('user_holding__holding__symbol')
    .annotate(total_net_amount=Sum('net_amount')).values_list('user_holding__holding__symbol', 'total_net_amount'))

    if not user_holdings:
        return render(request, 'dashboard.html', {
            'total_balance': wallet.balance,
            'available_balance': wallet.balance
        })
    
    # obtener estado actual del mercado
    market_state = yf.Ticker('VOO').info.get('marketState')

    #todo: obtener datos de yfinance

    symbols = [h.holding.symbol for h in user_holdings]

    if trades:
        # conseguir primer trade para obtener la fecha desde la que se van a descargar datos
        #! puede fallar si la bolsa permanece cerrada más de lo normal
        first_trade_date = trades[0].date - timedelta(days=10) 

        # descargar datos historicos
        history_data = yf.download(tickers=symbols, start=first_trade_date, interval="1d", prepost=True, group_by='ticker', threads=True)
    else:
        history_data = yf.download(tickers=symbols, period="5d", interval="1d", prepost=True, group_by='ticker', threads=True)

    # conseguir el último precio
    day_data = yf.download(tickers=symbols, period='1d', interval='1m', prepost=True, group_by='ticker')

    #todo: calcular total de acciones y manejar lotes para el calculo de ganancia no realizada

    holdings_data = {}
    
    for t in trades:

        # registrar símbolo en el diccionario si no existe
        if t.user_holding.holding.symbol not in holdings_data.keys():
            holdings_data[t.user_holding.holding.symbol] = {
                'total_shares': 0,
                'lots': [],
                'realized_gain': 0
            }

        if t.type == 'B': # compras
            holdings_data[t.user_holding.holding.symbol]['total_shares'] += t.shares
            # calcular el precio por acción considerando comisiones (incluidas en el total)
            price_per_share = t.total / t.shares
            # registrar la fecha, acciones y precio con comissiones por acción para los lotes (compras) 
            holdings_data[t.user_holding.holding.symbol]['lots'].append({'date': t.date,
                                                            'shares': t.shares,
                                                            'price_per_share': price_per_share})
        else: # ventas
            holdings_data[t.user_holding.holding.symbol]['total_shares'] -= t.shares

            partial_shares = None
            for i in range(0, len(holdings_data[t.user_holding.holding.symbol]['lots'])):
                #* si el primer lote (mas antiguo) tiene la suficiente cantidad para cubrir una venta se le resta y termina el bucle
                #* caso contrario, se lleva a 0, se guarda lo sobrante y se le resta al próximo lote
                #* repitiendo el proceso hasta cubrir la venta por completo

                # validar si en la iteración viene una parte de otro lote
                if not partial_shares:
                    holdings_data[t.user_holding.holding.symbol]['lots'][i]['shares'] -= t.shares
                else:
                    holdings_data[t.user_holding.holding.symbol]['lots'][i]['shares'] -= partial_shares

                # validar cuando el lote no haya pudido cubrir la venta por completo
                if holdings_data[t.user_holding.holding.symbol]['lots'][i]['shares'] < 0:
                    if partial_shares and partial_shares > 0:
                        t.shares = partial_shares

                    partial_shares = abs(holdings_data[t.user_holding.holding.symbol]['lots'][i]['shares'])
                    holdings_data[t.user_holding.holding.symbol]['realized_gain'] += (t.price * (t.shares - partial_shares)) - ((t.shares - partial_shares) * holdings_data[t.user_holding.holding.symbol]['lots'][i]['price_per_share'])

                    holdings_data[t.user_holding.holding.symbol]['lots'][i]['shares'] = 0

                    continue

                if not partial_shares:
                    holdings_data[t.user_holding.holding.symbol]['realized_gain'] += (t.price * t.shares) - (t.shares * holdings_data[t.user_holding.holding.symbol]['lots'][i]['price_per_share'])
                else:
                    holdings_data[t.user_holding.holding.symbol]['realized_gain'] += (t.price * partial_shares) - (partial_shares * holdings_data[t.user_holding.holding.symbol]['lots'][i]['price_per_share'])

                holdings_data[t.user_holding.holding.symbol]['realized_gain'] = round(holdings_data[t.user_holding.holding.symbol]['realized_gain'] - t.commission, 2)
                # terminar el bucle cuando se haya cubrido la ventas con los lotes
                break

    #todo: listado de última compra por activo y datos para la gráfica de distruciones    

    last_holdings_buy = {}
    type_distribution = {
        'ETF': 0,
        'ACCIÓN': 0,
        'CRIPTO': 0,
    }
    holding_distribution = {}

    #todo: calcular datos de los activos y los totales de la cartera

    total_current_invested_value = 0
    total_cost_per_lot = 0
    total_unrealized_gain = 0
    total_unrealized_gain_percent = 0
    total_realized_gain = 0
    total_gain = 0

    for h in user_holdings:

        # obtener precio del dia anterior y el más actual
        last_day_price = Decimal(history_data.get(h.holding.symbol).get('Close').dropna().iloc[-2])
        h.price = Decimal(day_data.get(h.holding.symbol).get('Close').dropna().iloc[-1])

        # cambio del dia del activo
        h.day_change = h.price  - last_day_price
        h.day_change_percent = h.day_change / h.price  * 100

        # obtener símbolo del activo (quitar "-USD" de las criptomonedas)
        logo_symbol = h.holding.symbol.split('-')[0] if '-' in h.holding.symbol else h.holding.symbol
        h.logo_url = f'https://img.logo.dev/ticker/{logo_symbol}?token={settings.LOGODEV_TOKEN}&size=40'

        
        h.shares = holdings_data[h.holding.symbol]['total_shares'] if holdings_data.get(h.holding.symbol) else 0

        # valor actual del activo en cartera y sumatoria a su total
        h.total_current_invested_value = h.shares * h.price
        total_current_invested_value += h.total_current_invested_value

        # valor de inversión inicial y sumatoria a su total
        h.cost_per_lot = 0

        if holdings_data.get(h.holding.symbol):
            h.cost_per_lot = sum([lot['shares'] * lot['price_per_share'] for lot in holdings_data[h.holding.symbol]['lots']])

        total_cost_per_lot += h.cost_per_lot

        # ganancia no realizada y sumatoria a su total      
        h.unrealized_gain = Decimal(h.total_current_invested_value - h.cost_per_lot) if h.cost_per_lot else 0
        h.unrealized_gain_percent = (h.unrealized_gain / h.cost_per_lot) * 100 if h.cost_per_lot else 0
        total_unrealized_gain += h.unrealized_gain

        if dividends.get(h.holding.symbol): 
            h.realized_gain = holdings_data[h.holding.symbol]['realized_gain'] + dividends.get(h.holding.symbol)
        else:
            h.realized_gain = holdings_data[h.holding.symbol]['realized_gain']

        total_realized_gain += h.realized_gain

        h.total_gain = h.realized_gain + h.unrealized_gain

        if h.shares > 0:
            # calcular dias desde la última compra
            last_holdings_buy[h.holding.symbol] = (date.today() - holdings_data[h.holding.symbol]['lots'][-1]['date']).days

            # agregar el valor actual del activo a la sumatoria de su tipo e individual para las gráficas
            if h.holding.type == 'ETF':
                type_distribution['ETF'] += h.total_current_invested_value
            elif h.holding.type == 'EQUITY':
                type_distribution['ACCIÓN'] += h.total_current_invested_value
            elif h.holding.type == 'CRYPTOCURRENCY':
                type_distribution['CRIPTO'] += h.total_current_invested_value

            holding_distribution[h.holding.symbol] = h.total_current_invested_value 

    #todo: sumatoria de totales y ordenamiento para la gráfica

    total_balance = total_current_invested_value + wallet.balance

    # distribución por activo y efectivo
    total_holding_distribution = sum([value for value in holding_distribution.values()]) + wallet.balance

    if total_current_invested_value > 0:

        for key in holding_distribution.keys():
            holding_distribution[key] = round(holding_distribution[key] / total_holding_distribution * 100, 2)

        holding_distribution['Efectivo'] = round(wallet.balance / total_holding_distribution * 100, 2)
    
        holding_distribution = {k: v for k, v in sorted(holding_distribution.items(), key=lambda item: item[1], reverse=True)}

        # tipo de distribución
        type_distribution_total = sum([value for value in type_distribution.values()])

        for key in type_distribution.keys():
            type_distribution[key] = round(type_distribution[key] / type_distribution_total * 100, 2)

        type_distribution = {k: v for k, v in sorted(type_distribution.items(), key=lambda item: item[1], reverse=True)}

        # porcentaje de la ganancia no realizada total

        total_unrealized_gain_percent = (total_unrealized_gain / total_current_invested_value) * 100

        # ordenar de menor a mayor las últimas compras por activo

        last_holdings_buy = {k: v for k, v in sorted(last_holdings_buy.items(), key=lambda item: item[1])}

        total_gain = total_unrealized_gain + total_realized_gain

    #todo: validar consistencia de datos

    if wallet.balance < 0:
        messages.warning(request, 'Tu balance disponible no debería ser negativo. Verifica la integridad histórica de tus registros.')
    
    context = {
        'holdings': user_holdings,
        'market_state': market_state,
        'available_balance': wallet.balance,
        'total_current_invested_value': total_current_invested_value,
        'total_balance': total_balance,
        'last_holdings_buy': last_holdings_buy,
        'total_unrealized_gain': total_unrealized_gain,
        'total_cost_per_lot': total_cost_per_lot,
        'type_distribution': type_distribution,
        'holding_distribution': holding_distribution,
        'total_unrealized_gain_percent': total_unrealized_gain_percent,
        'total_realized_gain': total_realized_gain,
        'total_gain': total_gain
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

    user = request.user

    user_holding = get_object_or_404(UserHolding, id=request.POST.get('id'), user=user)

    holding_symbol = user_holding.holding.symbol

    trades = Trade.objects.filter(user_holding=user_holding).order_by('-date', '-id')

    wallet = get_object_or_404(Wallet, user=user)

    with transaction.atomic():

        for trade in trades:
            wallet.balance = wallet.balance + trade.total if trade.type == 'B' else wallet.balance - trade.total

        wallet.save()
        user_holding.delete()
        
    messages.success(request, 'Símbolo Eliminado de la cartera.')

    return redirect('holding', symbol=holding_symbol)


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

    holding_object = Holding.objects.filter(symbol=symbol).first()

    exist = UserHolding.objects.filter(user=user, holding=holding_object).first()

    trade = Trade.objects.filter(user=user, user_holding=exist).order_by('-date', '-id')

    dividend = Dividend.objects.filter(user_holding=exist).order_by('-date', '-id')

    ernings = holding.financials

    # print(ernings.__dict__)

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

    form = TradeForm()
    # auto_id distinto para que los ids no choquen con los del TradeForm (id_date, id_commission...)
    dividend_form = DividendForm(auto_id='div_%s')

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
        'exist': exist,
        'form': form,
        'title': 'Registrar trade',
        'button': 'Registrar',
        'trade': trade,
        'holding_id': holding_object.id,
        'editing_trade_id': None,
        'dividend_form': dividend_form,
        'dividend': dividend,
        'editing_dividend_id': None,
        # vista que se muestra al cargar: 'trades' (por defecto) o 'dividends'
        'active_view': 'dividends' if request.GET.get('view') == 'dividends' else 'trades',
    }

    if request.method == 'POST':

        # Formulario de dividendos (registrar / editar): se procesa aparte
        if request.POST.get('is_dividend'):
            context['active_view'] = 'dividends'
            return _save_dividend(request, exist, holding_object, context)

        trade_id = request.POST.get('trade_id')
        old_trade = None

        if trade_id:
            # Solo puede editar trades propios y de este holding
            old_trade = get_object_or_404(Trade, id=trade_id, user=user, user_holding=exist)

            # OJO: guardar lo viejo ANTES de crear el form (ver explicación abajo)
            old_type = old_trade.type
            old_total = old_trade.total

            form = TradeForm(request.POST, instance=old_trade)
            context['title'] = 'Editar trade'
            context['button'] = 'Actualizar'
            context['editing_trade_id'] = old_trade.id
        else:
            form = TradeForm(request.POST)

        context['form'] = form

        if not form.is_valid():
            messages.error(request, 'No fue posible realizar la acción.')
            return render(request, 'holding.html', context)

        with transaction.atomic():

            trade = form.instance
            trade.user = user
            trade.user_holding = exist

            wallet = get_object_or_404(Wallet, user=user)

            if old_trade:
                # 1) Deshacer el efecto del trade viejo en la wallet
                wallet.balance = wallet.balance + old_total if old_type == 'B' else wallet.balance - old_total

            # 2) Aplicar el efecto del trade nuevo (igual que antes)
            wallet.balance = wallet.balance - trade.total if trade.type == 'B' else wallet.balance + trade.total

            trade.save()
            wallet.save()

            messages.success(request, 'Trade actualizado.' if old_trade else 'Trade agregado.')
            return redirect('holding', holding_object.symbol)
    
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

    wallet_transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-date', '-id')

    context = {
        'wallet_transactions': wallet_transactions,
        'balance': wallet.balance,
        'form': WalletTransactionForm(),
        'title': 'Registrar transacción',
        'button': 'Registrar',
        'editing_transaction_id': None,
    }

    if request.method == 'POST':

        transaction_id = request.POST.get('transaction_id')
        old_transaction = None

        if transaction_id:
            # Solo puede editar transacciones de su propia wallet
            old_transaction = get_object_or_404(WalletTransaction, id=transaction_id, wallet=wallet)

            # Guardar lo viejo ANTES de crear el form: is_valid() sobrescribe la instancia
            old_type = old_transaction.type
            old_net_amount = old_transaction.net_amount
            old_total = old_transaction.total
            old_commission = old_transaction.commission

            form = WalletTransactionForm(request.POST, instance=old_transaction)
            context.update(title='Editar transacción', button='Actualizar',
                           editing_transaction_id=old_transaction.id)
        else:
            form = WalletTransactionForm(request.POST)

        context['form'] = form

        if not form.is_valid():
            messages.error(request, 'No fue posible realizar la acción.')
            return render(request, 'wallet_transactions.html', context)

        with transaction.atomic():
            wallet_transaction = form.instance
            wallet_transaction.wallet = wallet

            if old_transaction:
                # 1) Deshacer el efecto de la transacción vieja (igual que en delete)
                wallet.balance = wallet.balance - old_net_amount if old_type == 'D' else wallet.balance + old_total
                wallet.commission_paid -= old_commission

            wallet_transaction.save()

            # 2) Aplicar el efecto de la nueva (igual que antes)
            wallet.balance = wallet.balance + wallet_transaction.net_amount if wallet_transaction.type == 'D' else wallet.balance - wallet_transaction.total
            wallet.commission_paid += wallet_transaction.commission
            wallet.save()

        messages.success(request, 'Transacción actualizada.' if old_transaction else 'Transacción registrada.')
        return redirect('wallet_transactions')

    return render(request, 'wallet_transactions.html', context)

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

    messages.success(request, 'Transacción eliminada.')

    return redirect('wallet_transactions')

@login_required
def delete_trade(request):

    user = request.user

    holding_id = request.POST.get('holding_id')
    trade_id = request.POST.get('trade_id')

    trade = Trade.objects.filter(id=trade_id).first()
    holding = Holding.objects.filter(id=holding_id).first()

    wallet = get_object_or_404(Wallet, user=user)

    with transaction.atomic():

        wallet.balance = wallet.balance + trade.total if trade.type == 'B' else wallet.balance - trade.total
        wallet.save()
        trade.delete()
        messages.success(request, 'Trade eliminado.')
        return redirect('holding', holding.symbol)
    
    messages.error(request, 'Algo salió mal.')
    return redirect('holding', holding.symbol)

def _dividend_wallet_effect(dividend):
    """Cuánto suma un dividendo a la wallet. Los reinvertidos no tocan el efectivo.
    Si el efectivo debe recibir el total (neto de comisión) en vez de net_amount, cámbialo aquí."""
    return Decimal(0) if dividend.reinvested else dividend.net_amount


def _dividend_redirect(holding_object):
    """Vuelve al holding abriendo directamente la vista de dividendos."""
    return redirect(f"{reverse('holding', args=[holding_object.symbol])}?view=dividends")


def _save_dividend(request, user_holding, holding_object, context):
    """Registra o edita un dividendo y ajusta la wallet."""

    user = request.user

    if not user_holding:
        messages.error(request, 'Debes tener el activo en tu cartera para registrar dividendos.')
        return _dividend_redirect(holding_object)

    dividend_id = request.POST.get('dividend_id')
    old_dividend = None

    if dividend_id:
        # Solo puede editar dividendos propios y de este holding
        old_dividend = get_object_or_404(Dividend, id=dividend_id, user_holding=user_holding)

        # Guardar lo viejo ANTES de crear el form: is_valid() sobrescribe la instancia
        old_effect = _dividend_wallet_effect(old_dividend)

        form = DividendForm(request.POST, instance=old_dividend, auto_id='div_%s')
        context['editing_dividend_id'] = old_dividend.id
    else:
        form = DividendForm(request.POST, auto_id='div_%s')

    context['dividend_form'] = form

    if not form.is_valid():
        messages.error(request, 'No fue posible realizar la acción.')
        return render(request, 'holding.html', context)

    with transaction.atomic():

        wallet = get_object_or_404(Wallet, user=user)

        dividend = form.instance
        dividend.user_holding = user_holding

        if old_dividend:
            # 1) Deshacer el efecto del dividendo viejo
            wallet.balance -= old_effect

        dividend.save()

        # 2) Aplicar el efecto del nuevo
        wallet.balance += _dividend_wallet_effect(dividend)
        wallet.save()

    messages.success(request, 'Dividendo actualizado.' if old_dividend else 'Dividendo registrado.')
    return _dividend_redirect(holding_object)


@login_required
def delete_dividend(request):

    if request.method != 'POST':
        return redirect('dashboard')

    user = request.user

    dividend = get_object_or_404(
        Dividend.objects.select_related('user_holding__holding'),
        id=request.POST.get('dividend_id'),
        user_holding__user=user,
    )

    holding_object = dividend.user_holding.holding

    wallet = get_object_or_404(Wallet, user=user)

    with transaction.atomic():
        wallet.balance -= _dividend_wallet_effect(dividend)
        wallet.save()
        dividend.delete()

    messages.success(request, 'Dividendo eliminado.')
    return _dividend_redirect(holding_object)