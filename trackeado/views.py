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
import time
from pprint import pprint
from decimal import Decimal
from datetime import date, timedelta
from django.core.cache import cache
import pandas as pd
import math
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

###############################
# Inicio 
###############################
@login_required
def dashboard(request):

    #todo: obtener datos a utilizar

    user = request.user
    wallet = get_object_or_404(Wallet, user=user)
    wallet_transactions = WalletTransaction.objects.filter(wallet_id=wallet.id).order_by('date', 'id')
    user_holdings = UserHolding.objects.select_related('holding').filter(user=user)
    trades = Trade.objects.select_related('user_holding__holding').filter(user=user).order_by('date', 'id')
    dividends = Dividend.objects.select_related('user_holding__user').filter(user_holding__user=user).order_by('date', 'id')

    total_current_invested_value = Decimal(0)
    total_current_invested = Decimal(0)
    total_unrealized_gain = Decimal(0)
    total_unrealized_gain_percent = Decimal(0)
    total_realized_gain = Decimal(0)
    total_dividends = Decimal(0)
    total_gain = Decimal(0)

    # obtener view para mostrar en caso de errores
    view_name = request.resolver_match.view_name

    # obtener cambio
    currency = user.get_currency_display() 

    currency_code = f"USD{user.currency}=X"

    currency_rate = cache.get(currency_code)
    
    if not user_holdings:
        return render(request, 'dashboard.html', {
            'total_balance': wallet.balance,
            'total_balance_dop': convert_currency(wallet.balance, currency_rate, currency_code),
            'available_balance': wallet.balance,
            'total_current_invested': total_current_invested,
            'total_current_invested_dop': 0,
            'total_current_invested_value': total_current_invested_value,
            'total_current_invested_value_dop': 0,
            'total_unrealized_gain': total_unrealized_gain,
            'total_unrealized_gain_dop': 0,
            'total_unrealized_gain_percent': total_unrealized_gain_percent,
            'total_realized_gain': total_realized_gain,
            'total_realized_gain_dop': 0,
            'total_dividends': total_dividends,
            'total_dividends_dop': 0,
            'total_gain': total_gain,
            'total_gain_dop': 0,
            'market_state': get_market_status(request, view_name),
            'twr': 0,
            'net_annual_dividends': 0,
            'net_annual_dividends_dop': 0,
            'net_annual_dividends_percent': 0,
            'currency': currency
        })

    #todo: obtener datos de yfinance

    symbols = [h.holding.symbol for h in user_holdings]

    # Crear una llave única para el usuario y sus símbolos actuales
    # Ordenar los símbolos para que ['VOO', 'GOOGL'] genere la misma llave que ['GOOGL', 'VOO']
    symbols_key = "_".join(sorted(symbols))
    cache_key = f"history_data_{user.id}_{symbols_key}"

    history_data = cache.get(cache_key)

    if trades:
        # conseguir primer trade para obtener la fecha desde la que se van a descargar datos
        #! puede fallar si la bolsa permanece cerrada más de lo normal
        first_trade_date = trades[0].date - timedelta(days=10)

        # limitar fechas válidas para descargar datos
        if first_trade_date < date(1950, 1, 1) or first_trade_date > date.today():
            first_trade_date = date(1950, 1, 1)

        if history_data is None:
            # descargar datos historicos
            try:
                history_data = yf.download(tickers=symbols, start=first_trade_date, interval="1d", prepost=True, group_by='ticker', threads=True)
                cache.set(cache_key, history_data, timeout=3600)
            except Exception:
                logger.exception('Error descargando datos históricos')
                return render(request, '500.html', {}, status=500)
    else:
        if history_data is None:
            try:
                history_data = yf.download(tickers=symbols, period="5d", interval="1d", prepost=True, group_by='ticker', threads=True)
                cache.set(cache_key, history_data, timeout=3600)
            except Exception:
                logger.exception('Error descargando datos históricos')
                return render(request, '500.html', {}, status=500)

    # conseguir el último precio
    try:
        day_data = yf.download(tickers=symbols, period='1d', interval='1m', prepost=True, group_by='ticker')
    except Exception:
        logger.exception('Error descargando datos del día')
        return render(request, '500.html', {}, status=500)

    #todo: última compra por activo y datos para la gráfica de distruciones

    last_holdings_buy = {}
    type_distribution = {
        'ETF': 0,
        'ACCIÓN': 0,
        'CRIPTO': 0,
    }
    holding_distribution = {}
    risk_distribution = {
        'Medio': 0,
        'Medio alto': 0,
        'Alto': 0,
        'Muy alto': 0,
     }

    #todo: calcular datos de los activos y los totales de la cartera

    symbols_active = []

    for h in user_holdings:

        # obtener precio del dia anterior y el más actual
        #! cubrir de otra manera el escenario en el que faltan muchos o todos
        try:
            last_day_price = Decimal(history_data.get(h.holding.symbol).get('Close').dropna().iloc[-2])
        except IndexError:
            try:
                last_day_price = Decimal(yf.Ticker(h.holding.symbol).info.get('previousClose'))
            except Exception:
                last_day_price = 1
                logger.exception(f'No fue posible consultar el precio del cierre anterior de {h.holding.symbol}.')
                messages.error(request, f'No fue posible consultar el precio del cierre anterior de {h.holding.symbol}. Los cálculos podrían verse afectados.')

        h.price = Decimal(day_data.get(h.holding.symbol).get('Close').dropna().iloc[-1])

        # cambio del dia del activo
        h.day_change = h.price - last_day_price
        h.day_change_percent = h.day_change / last_day_price * 100

        # obtener símbolo del activo (quitar "-USD" de las criptomonedas)
        logo_symbol = h.holding.symbol.split('-')[0] if '-' in h.holding.symbol else h.holding.symbol
        h.logo_url = f'https://img.logo.dev/ticker/{logo_symbol}?token={settings.LOGODEV_TOKEN}&size=40'

        if trades:
            # filtrar por el activo actual
            holding_trades = [t for t in trades if t.user_holding_id == h.id]
            holding_dividends = [d for d in dividends if d.user_holding_id == h.id]

            # calcular métricas
            h_metrics = holding_metrics(holding_trades, holding_dividends, h.price)

            h.shares = h_metrics['total_shares']
            h.current_invested_value = h_metrics['current_invested_value']
            h.current_invested = h_metrics['current_invested']
            h.unrealized_gain = h_metrics['unrealized_gain']
            h.unrealized_gain_percent = h_metrics['unrealized_gain_percent']
            h.realized_gain = h_metrics['realized_gain']
            h.dividends = h_metrics['total_dividends']
            h.total_gain = h_metrics['total_gain']

            total_current_invested_value += h.current_invested_value
            total_current_invested += h.current_invested
            total_unrealized_gain += h.unrealized_gain
            total_dividends += h.dividends
            total_realized_gain += h.realized_gain

            if h.dividends == 0:
                h.dividends = None

            if h.current_invested > 0:
                # calcular dias desde la última compra
                for i in range(len(h_metrics['lots']) - 1, -1, -1):
                    if h_metrics['lots'][i]['type'] == 'B':
                        last_holdings_buy[h.holding.symbol] = (date.today() - h_metrics['lots'][i]['date']).days
                        break

                # agregar el valor actual del activo a la sumatoria de su tipo e individual para las gráficas
                if h.holding.type == 'ETF':
                    type_distribution['ETF'] += h.current_invested_value
                elif h.holding.type == 'EQUITY':
                    type_distribution['ACCIÓN'] += h.current_invested_value
                elif h.holding.type == 'CRYPTOCURRENCY':
                    type_distribution['CRIPTO'] += h.current_invested_value

                holding_distribution[h.holding.symbol] = h.current_invested_value

                if h.risk == 'M':
                    risk_distribution['Medio'] += h.current_invested_value
                elif h.risk == 'MH':
                    risk_distribution['Medio alto'] += h.current_invested_value
                elif h.risk == 'H':
                    risk_distribution['Alto'] += h.current_invested_value
                elif h.risk == 'VH':
                    risk_distribution['Muy alto'] += h.current_invested_value

            if h.shares > 0:
                symbols_active.append(h.holding.symbol)

    #todo: calcular estimación de dividendos netos anuales
    
    def get_estimated_annual_dividends(symbol):

        #! cubrir el escenario en el que faltan muchos o todos
        try:
            raw_yield = yf.Ticker(symbol).info.get('dividendYield')
        except Exception:
            logger.exception(f'No fue posible consultar consultar el dividendo anual de {symbol}.')
            messages.error(request, f'No fue posible consultar consultar el dividendo anual de {symbol}. Los cálculos podrían verse afectados.')

        if not raw_yield:
            raw_yield = 0.0

        for h in user_holdings:
            if h.holding.symbol == symbol:
                holding_current_invested_value = h.current_invested_value
                break

        return holding_current_invested_value * Decimal(raw_yield * 0.70 / 100)

    with ThreadPoolExecutor(max_workers=50) as executor:
        net_annual_dividends = sum(list(executor.map(get_estimated_annual_dividends, symbols_active)))
    
    total_balance = total_current_invested_value + wallet.balance

    if total_balance > 0:
        net_annual_dividends_percent = (net_annual_dividends / total_balance) * 100
    else:
        net_annual_dividends_percent = 0

    #todo: sumatoria de totales y ordenamiento para la gráfica

    # total invertido y incluyendo efectivo
    total_invested_and_cash = sum([value for value in holding_distribution.values()]) + wallet.balance

    if total_current_invested > 0:

        for key in holding_distribution.keys():
            holding_distribution[key] = round(holding_distribution[key] / total_invested_and_cash * 100, 2)

        holding_distribution['Efectivo'] = round(wallet.balance / total_invested_and_cash * 100, 2)
    
        holding_distribution = {k: v for k, v in sorted(holding_distribution.items(), key=lambda item: item[1], reverse=True)}

        # tipo de distribución
        total_invested = sum([value for value in type_distribution.values()])

        for key in type_distribution.keys():
            type_distribution[key] = round(type_distribution[key] / total_invested * 100, 2)

        type_distribution = {k: v for k, v in sorted(type_distribution.items(), key=lambda item: item[1], reverse=True)}

        # distribución por riesgo
        for key in risk_distribution.keys():
            risk_distribution[key] = round((risk_distribution[key] / total_invested) * 100, 2)

        risk_distribution = {k: v for k, v in sorted(risk_distribution.items(), key=lambda item: item[1], reverse=True)}

        # porcentaje de la ganancia no realizada total

        total_unrealized_gain_percent = (total_unrealized_gain / total_current_invested_value) * 100

        # ordenar de menor a mayor las últimas compras por activo

        last_holdings_buy = {k: v for k, v in sorted(last_holdings_buy.items(), key=lambda item: item[1])}

        total_gain = total_unrealized_gain + total_realized_gain + total_dividends

    #todo: calculo del TWR

    #! falta validar cuando hay dos transacciones el mismo dia

    twr = 0

    if wallet_transactions and trades:
        
        subperiod = []

        for i in range(0, len(wallet_transactions)):

            subperiod.append({'start_date': wallet_transactions[i].date})

            if i == 0:
                subperiod[i]['start_value'] = wallet_transactions[i].net_amount
            else:
                subperiod[i-1]['end_date'] = wallet_transactions[i].date

        subperiod_wallet_balance = 0

        for i in range(0, len(subperiod)):

            subperiod_trade_balance = 0
            subperiod_dividend_balance = 0
            subperiod_balance = 0

            if wallet_transactions[i].type == 'D':
                subperiod_wallet_balance += wallet_transactions[i].net_amount
            else:
                subperiod_wallet_balance -= wallet_transactions[i].total

            if subperiod[i].get('end_date'):
                subperiod_trades = [t for t in trades if t.date < subperiod[i]['end_date']]
                subperiod_dividends = [d for d in dividends if d.date < subperiod[i]['end_date']]
            else:
                subperiod_trades = trades
                subperiod_dividends = dividends

            for trade in subperiod_trades:

                if trade.type in ['B', 'D']:
                    subperiod_trade_balance -= trade.total
                else:
                    subperiod_trade_balance += trade.total

            subperiod_dividend_balance += sum([d.net_amount for d in subperiod_dividends])

            for h in user_holdings:

                holding_trades = [t for t in subperiod_trades if t.user_holding_id == h.id]
                holding_dividends = [d for d in subperiod_dividends if d.user_holding_id == h.id]

                if not holding_trades:
                    continue

                if subperiod[i].get('end_date'):
                    end_date = subperiod[i]['end_date']

                    limit = 10

                    while True:
                        try:
                            price = history_data.loc[end_date.strftime('%Y-%m-%d'), (h.holding.symbol, 'Close')]
                            if pd.notna(price):
                                break
                        except KeyError:
                            pass
                        end_date -= timedelta(days=1)

                        limit -= 1

                        if limit == 0:
                            logger.exception(f'No se ha encontrado precio en {h.holding.symbol}')
                            return render(request, '500.html', {}, status=500)

                    price = Decimal(str(price))
                else:
                    price = Decimal(day_data.get(h.holding.symbol).get('Close').dropna().iloc[-1])

                h_metrics = holding_metrics(holding_trades, holding_dividends, price)

                subperiod_balance += h_metrics['current_invested_value']

            subperiod_balance += subperiod_wallet_balance + subperiod_dividend_balance + subperiod_trade_balance

            subperiod[i]['end_value'] = subperiod_balance

            if i + 1 < len(subperiod):
                if wallet_transactions[i + 1].type == 'D':
                    subperiod[i + 1]['start_value'] = subperiod[i]['end_value'] + wallet_transactions[i + 1].net_amount
                else:
                    subperiod[i + 1]['start_value'] = subperiod[i]['end_value'] - wallet_transactions[i + 1].total

            if subperiod[i]['start_value'] == 0:
                subperiod[i]['period_return'] = Decimal(0)
            else:
                subperiod[i]['period_return'] = (subperiod[i]['end_value'] - subperiod[i]['start_value']) / subperiod[i]['start_value']

        twr = (math.prod([subperiod[i]['period_return'] + 1 for i in range(0, len(subperiod))]) - 1) * 100

    else:
        twr = 0

    #todo: validar consistencia de datos

    if wallet.balance < 0:
        messages.warning(request, 'Tu balance disponible no debería ser negativo. Verifica la integridad histórica de tus registros.')
    context = {
        'market_state': get_market_status(request, view_name),
        'available_balance': wallet.balance,
        'total_current_invested_value': total_current_invested_value,
        'total_current_invested_value_dop': convert_currency(total_current_invested_value, currency_rate,currency_code),
        'total_balance': total_balance,
        'total_balance_dop': convert_currency(total_balance, currency_rate,currency_code),
        'total_unrealized_gain': total_unrealized_gain,
        'total_unrealized_gain_dop': convert_currency(total_unrealized_gain, currency_rate,currency_code),
        'total_current_invested': total_current_invested,
        'total_current_invested_dop': convert_currency(total_current_invested, currency_rate,currency_code),
        'total_unrealized_gain_percent': total_unrealized_gain_percent,
        'total_realized_gain': total_realized_gain,
        'total_realized_gain_dop': convert_currency(total_realized_gain, currency_rate,currency_code),
        'total_dividends': total_dividends,
        'total_dividends_dop': convert_currency(total_dividends, currency_rate,currency_code),
        'total_gain': total_gain,
        'total_gain_dop': convert_currency(total_gain, currency_rate,currency_code),
        'holdings': user_holdings,
        'last_holdings_buy': last_holdings_buy,
        'type_distribution': type_distribution,
        'holding_distribution': holding_distribution,
        'risk_distribution': risk_distribution,
        'twr': twr,
        'net_annual_dividends': net_annual_dividends,
        'net_annual_dividends_dop': convert_currency(net_annual_dividends, currency_rate,currency_code),
        'net_annual_dividends_percent': net_annual_dividends_percent,
        'currency': currency
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

                # obtener view para mostrar en caso de errores
                view_name = request.resolver_match.view_name

                ticker = get_holding(symbol, view_name)

                if not ticker:
                    messages.error(request, f'No fue posible obtener a {symbol} en este momento. Inténtalo más tarde.')
                    return redirect('dashboard')

                info = ticker.info

                if not info or ("regularMarketPrice" not in info and "longName" not in info and "shortName" not in info):
                    messages.success(request, 'Símbolo no encontrado.')
                    return redirect('dashboard')

                if info.get('currency') != 'USD':
                    messages.error(request, 'Solo se admite activos en USD')
                    return redirect('dashboard')

                name = ticker.info.get('longName')
                type = ticker.info.get('quoteType')
                sector = ticker.info.get('sector')

                holding = Holding.objects.create(symbol=symbol, name=name, sector=sector, type=type)
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
            if trade.type != 'D':
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

    watch_list = get_object_or_404(WatchList, name=watch_list, user=user)

    if user.id == watch_list.user.id:

        holdings_list = HoldingList.objects.select_related('holding').filter(watch_list=watch_list)

        if holdings_list:

            symbols = [h.holding.symbol for h in holdings_list]

            try:
                data = yf.download(tickers=symbols, period="5d", interval="1d", prepost=True, group_by='ticker', threads=True)
                data2 = yf.download(tickers=symbols, period="1d", interval="1m", prepost=True, group_by='ticker', threads=True)
            except Exception:
                logger.exception('Error obteniendo datos históricos de la lista')
                return render(request, '500.html', {}, status=500)

            for h in holdings_list:
                last_day_price = data.get(h.holding.symbol).get('Close').dropna().iloc[-2]
                current_price = round(data2.get(h.holding.symbol).get('Close').dropna().iloc[-1], 2)
                h.holding.day_change = round(current_price - last_day_price, 2)
                h.holding.day_change_percent = round(h.holding.day_change / current_price * 100, 2)

                h.holding.price = current_price

                logo_symbol = h.holding.symbol.split('-')[0] if '-' in h.holding.symbol else h.holding.symbol
                h.logo_url = f'https://img.logo.dev/ticker/{logo_symbol}?token={settings.LOGODEV_TOKEN}&size=40'
        
        return render(request, 'watch_list_details.html', {'holdings_list': holdings_list, 'watch_list': watch_list, 'market_state': get_market_status(request) })

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

                # obtener view para mostrar en caso de errores
                view_name = request.resolver_match.view_name

                ticker = get_holding(symbol, view_name)

                #! corregir redireccion en ambas
                if not ticker:
                    messages.error(request, f'No fue posible obtener a {symbol} en este momento. Inténtalo más tarde.')
                    return redirect('dashboard')   

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

    user = request.user

    if request.method == 'POST':

        holding_list_id = request.POST.get('holding_list_id')

        holding_list = get_object_or_404(HoldingList, id=holding_list_id)

        watch_list = holding_list.watch_list

        if user == watch_list.user:
            holding_list.delete()
            messages.success(request, 'Eliminado de la lista.')
            return redirect('watch_list_details', watch_list.name)
        else:
            messages.success(request, 'Acción no autorizada.')
            return redirect('watch_list_details', watch_list.name)

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

    # obtener view para mostrar en caso de errores
    view_name = request.resolver_match.view_name

    ticker = get_holding(symbol, view_name)

    if not ticker:
        messages.error(request, f'No fue posible obtener a {symbol} en este momento. Inténtalo más tarde.')
        return redirect('dashboard')  

    info = ticker.info

    if not info.get('symbol'):
        messages.error(request, 'Símbolo no encontrado')
        return redirect('dashboard')

    user_holding = UserHolding.objects.select_related('holding').filter(user=user, holding__symbol=symbol).first()

    earnings_df = ticker.financials
    
    q_earnings_df = ticker.quarterly_income_stmt

    earnings_data = {
        'date': [],
        'total_revenues': [],
        'net_incomes': [],
        'net_margins': []
    }

    q_earnings_data = {
        'date': [],
        'total_revenues': [],
        'net_incomes': [],
        'net_margins': []
    }

    # Extraer y ordenar directamente con tu variable
    if info.get('quoteType') == 'EQUITY':
        rev = earnings_df.loc['Total Revenue'].dropna().iloc[::-1]
        net = earnings_df.loc['Net Income'].dropna().iloc[::-1]

        earnings_data['date'] = [d.strftime('%Y') for d in rev.keys()]
        earnings_data['total_revenues'] = [v for v in rev.values]
        earnings_data['net_incomes'] = [v for v in net.values]
        earnings_data['net_margins'] = []

        for x in range(0, len(earnings_data['date'])):
            if earnings_data['total_revenues'][x] != 0:
                net_margins = earnings_data['net_incomes'][x] / earnings_data['total_revenues'][x] * 100

                earnings_data['net_margins'].append(net_margins)
            else:
                earnings_data['net_margins'].append(None)

        q_rev = q_earnings_df.loc['Total Revenue']
        q_net = q_earnings_df.loc['Net Income']

        valid = q_rev.notna() & q_net.notna()

        q_rev = q_rev[valid].iloc[::-1]
        q_net = q_net[valid].iloc[::-1]

        q_earnings_data['date'] = [str(d.to_period('Q')) for d in q_rev.index]

        q_earnings_data['total_revenues'] = q_rev.tolist()
        q_earnings_data['net_incomes'] = q_net.tolist()

        q_earnings_data['net_margins'] = [
            round((net / rev) * 100)
            for rev, net in zip(
                q_earnings_data['total_revenues'],
                q_earnings_data['net_incomes']
            )
            if rev != 0
        ]

    try:
        df = ticker.history(period="max")
        df_5d = ticker.history(period="5d", interval="15m", prepost=True)
        df_1d = ticker.history(period="1d", interval="5m", prepost=True)
    except Exception:
        logger.exception(f'No fue posible obtener el historial de {symbol}')
        return render(request, '500.html', {}, status=500)

    # 1. Asegurar la zona horaria correcta (Nueva York) antes de extraer la hora
    for d in [df_5d, df_1d]:
        if not d.empty:
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
    if not df_5d.empty:
        df_5d['Phase'] = df_5d.index.map(get_market_phase)
    if not df_1d.empty:
        df_1d['Phase'] = df_1d.index.map(get_market_phase)

    # 4. Reseteamos el índice
    df.reset_index(inplace=True)
    df_5d.reset_index(inplace=True)
    df_1d.reset_index(inplace=True)

    # 5. Formateamos las fechas a string de forma segura
    if 'Date' in df.columns and not df.empty:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
    else:
        df['Date'] = []

    if 'Datetime' in df_5d.columns and not df_5d.empty:
        df_5d['Datetime'] = pd.to_datetime(df_5d['Datetime'], errors='coerce').astype(str)
    else:
        df_5d['Datetime'] = []

    if 'Datetime' in df_1d.columns and not df_1d.empty:
        df_1d['Datetime'] = pd.to_datetime(df_1d['Datetime'], errors='coerce').astype(str)
    else:
        df_1d['Datetime'] = []

    # 6. Convertimos a diccionarios, incluyendo 'Phase' en los de corto plazo
    history_list = df[['Date', 'Close']].dropna(subset=['Close']).to_dict(orient='records') if 'Close' in df.columns else []
    history_list_5d = df_5d[['Datetime', 'Close', 'Phase']].dropna(subset=['Close']).to_dict(orient='records') if {'Datetime', 'Close', 'Phase'}.issubset(df_5d.columns) else []
    history_list_1d = df_1d[['Datetime', 'Close', 'Phase']].dropna(subset=['Close']).to_dict(orient='records') if {'Datetime', 'Close', 'Phase'}.issubset(df_1d.columns) else []

    for h in history_list_5d:
        h['Close'] = round(float(h['Close']), 2)
    for h in history_list_1d:
        h['Close'] = round(float(h['Close']), 2)
    for h in history_list:
        h['Close'] = round(float(h['Close']), 2)

    # Precio de respaldo si no hay velas intradía todavía
    fallback_price = (
        history_list_1d[-1]['Close'] if history_list_1d
        else history_list_5d[-1]['Close'] if history_list_5d
        else history_list[-1]['Close'] if history_list
        else info.get('currentPrice') or info.get('regularMarketPrice') or 0
    )

    if history_list:
        history_list[-1]['Close'] = fallback_price
    if history_list_5d:
        history_list_5d[-1]['Close'] = fallback_price

    logo_symbol = symbol.split('-')[0] if '-' in symbol else symbol

    form = TradeForm()
    # auto_id distinto para que los ids no choquen con los del TradeForm (id_date, id_commission...)
    dividend_form = DividendForm(auto_id='div_%s')

    context = {
        'symbol': symbol.upper(),
        'longName': info.get('longName'),
        'quoteType': info.get('quoteType'),
        'postMarketPrice': info.get('postMarketPrice'),
        'dayHigh':  info.get('dayHigh'),
        'dayLow':  info.get('dayLow'),
        'dividendYield':  info.get('dividendYield'),
        'fullExchangeName': info.get('fullExchangeName'),
        'fulldayChange': info.get('fulldayChange'),
        'fulldayChangePercent': info.get('fulldayChangePercent'),
        'postMarketChange': info.get('postMarketChange'),
        'postMarketChangePercent': info.get('postMarketChangePercent'),
        'industry': info.get('industry'),
        'marketCap': info.get('marketCap'),
        'sector': info.get('sector'),
        'targetHighPrice': info.get('targetHighPrice'),
        'targetLowPrice': info.get('targetLowPrice'),
        'targetMeanPrice': info.get('targetMeanPrice'),
        'targetMedianPrice': info.get('targetMedianPrice'),
        'trailingPE': info.get('trailingPE'),
        'forwardPE': info.get('forwardPE'),
        'beta': info.get('beta'),
        'trailingEps': info.get('trailingEps'),
        'volume': info.get('volume'),
        'averageVolume': info.get('averageVolume'),
        'fullTimeEmployees': info.get('fullTimeEmployees'),
        'sharesOutstanding': info.get('sharesOutstanding'),
        'averageVolume10days': info.get('averageVolume10days'),
        'marketState': info.get('marketState'),
        'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh'),
        'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow'),
        'recommendationKey': info.get('recommendationKey'),
        'history_list': history_list,
        'history_list_5d': history_list_5d,
        'history_list_1d': history_list_1d,
        'logo_url': f"https://img.logo.dev/ticker/{logo_symbol}?token={settings.LOGODEV_TOKEN}&size=40",
        'user_holding': user_holding,
        'form': form,
        'title': 'Registrar orden / reinversión',
        'button': 'Registrar',
        'editing_trade_id': None,
        'dividend_form': dividend_form,
        'editing_dividend_id': None,
        # vista que se muestra al cargar: 'trades' (por defecto) o 'dividends'
        'active_view': 'dividends' if request.GET.get('view') == 'dividends' else 'trades',
        'earnings_data': earnings_data,
        'q_earnings_data': q_earnings_data,
    }

    if user_holding:

        trade = Trade.objects.filter(user_holding=user_holding).order_by('date', 'id')
        dividend = Dividend.objects.filter(user_holding=user_holding).order_by('-date', '-id')
        h_metrics = holding_metrics(trade, dividend, Decimal(history_list_1d[-1]['Close']))

        for t in trade:
            if t.type == 'S':
                t.realized_gain = h_metrics['gain_per_sell'].get(t.id)
            else:
                t.realized_gain = None

        context['trade'] = trade
        context['dividend'] = dividend
        context['h_metrics'] = h_metrics

    if request.method == 'POST':

        # Formulario de dividendos (registrar / editar): se procesa aparte
        if request.POST.get('is_dividend'):
            context['active_view'] = 'dividends'
            return _save_dividend(request, user_holding, context)

        trade_id = request.POST.get('trade_id')
        old_trade = None

        if trade_id:
            # Solo puede editar trades propios y de este holding
            old_trade = get_object_or_404(Trade, id=trade_id, user=user, user_holding=user_holding)

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
            trade.user_holding = user_holding

            wallet = get_object_or_404(Wallet, user=user)

            if trade.type != 'D':

                if old_trade:
                    # 1) Deshacer el efecto del trade viejo en la wallet
                    wallet.balance = wallet.balance + old_total if old_type == 'B' else wallet.balance - old_total

                # 2) Aplicar el efecto del trade nuevo (igual que antes)
                wallet.balance = wallet.balance - trade.total if trade.type == 'B' else wallet.balance + trade.total

                wallet.save()
                trade.save()
            else:
                if old_trade:
                    dividend = get_object_or_404(Dividend, reinvested=trade)
                    dividend.net_amount = trade.net_amount
                    dividend.commission = trade.commission
                    dividend.date = trade.date
                    dividend.save()
                    trade.save()
                else:
                    trade.save()
                    Dividend.objects.create(user_holding=user_holding, net_amount=trade.net_amount, commission=trade.commission, reinvested=trade, date=trade.date)

            messages.success(request, 'Trade actualizado.' if old_trade else 'Trade agregado.')
            return redirect('holding', user_holding.holding.symbol)
    
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

        if trade.type != 'D':
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
    # return Decimal(0) if dividend.reinvested else dividend.net_amount
    return dividend.net_amount


def _dividend_redirect(holding_object):
    """Vuelve al holding abriendo directamente la vista de dividendos."""
    return redirect(f"{reverse('holding', args=[holding_object.symbol])}?view=dividends")


def _save_dividend(request, user_holding, context):
    """Registra o edita un dividendo y ajusta la wallet."""

    user = request.user

    if not user_holding:
        messages.error(request, 'Debes tener el activo en tu cartera para registrar dividendos.')
        return _dividend_redirect(user_holding.holding)

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
    return _dividend_redirect(user_holding.holding)


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

@login_required
def update_holding_risk(request):

    user = request.user

    user_holding_id = request.POST.get('user_holding_id')
    risk = request.POST.get('risk')

    user_holding =  get_object_or_404(UserHolding, id=user_holding_id, user=user)

    if risk in ['M', 'MH', 'H', 'VH']:
        user_holding.risk = risk
        user_holding.save()
        messages.success(request, 'Nivel de riesgo actualizado.')
    else:
        messages.error(request, 'Opcion no válida')
    
    return redirect('holding', symbol=user_holding.holding.symbol)


###############################
# Funciones
###############################

# calcular métricas de activos   
def holding_metrics(trades, dividends, current_price):
    '''Calcular métricas por activo como: inversión actual, valor de la inversión acutal,
    dividendos recibidos, ganancia no realizada, ganancia realizada y ganancia total  
    '''

    total_dividends = sum([d.net_amount for d in dividends]) if dividends else 0

    h_metrics = {
        'lots': [],
        'current_invested': 0,
        'total_shares': 0,
        'realized_gain': 0,
        'total_dividends': total_dividends,
        'current_invested_value': 0,
        'unrealized_gain': 0,
        'unrealized_gain_percent': 0,
        'total_gain': 0
    }

    h_metrics['gain_per_sell'] = {}
    last_realized_gain = 0

    for t in trades:

        shares = t.shares

        if t.type in ['B', 'D']: # compras
            h_metrics['total_shares'] += shares
            # calcular el precio por acción considerando comisiones (incluidas en el total)
            if t.type == 'B':
                price_per_share = t.total / shares
            else:
                price_per_share = t.net_amount / shares
            # registrar la fecha, acciones y precio con comissiones por acción para los lotes (compras) 
            h_metrics['lots'].append({'date': t.date,
                                    'shares': shares,
                                    'price_per_share': price_per_share,
                                    'type': t.type})
        else: # ventas
            h_metrics['total_shares'] -= shares

            partial_shares = None
            for h in h_metrics['lots']:
                #* si el primer lote (mas antiguo) tiene la suficiente cantidad para cubrir una venta se le resta y termina el bucle
                #* caso contrario, se lleva a 0, se guarda lo sobrante y se le resta al próximo lote
                #* repitiendo el proceso hasta cubrir la venta por completo

                # validar si en la iteración viene una parte de otro lote
                if not partial_shares:
                    h['shares'] -= shares
                else:
                    h['shares'] -= partial_shares

                # validar cuando el lote no haya podido cubrir la venta por completo
                if h['shares'] < 0:
                    if partial_shares and partial_shares > 0:
                        shares = partial_shares

                    # guarda el sobrante
                    partial_shares = abs(h['shares'])

                    h['shares'] = 0

                    h_metrics['realized_gain'] += (t.price * (shares - partial_shares)) - ((shares - partial_shares) *h['price_per_share'])

                    continue

                if not partial_shares:
                    h_metrics['realized_gain'] += (t.price * shares) - (shares * h['price_per_share'])
                else:
                    h_metrics['realized_gain'] += (t.price * partial_shares) - (partial_shares * h['price_per_share'])

                h_metrics['realized_gain'] -= t.commission

                if not h_metrics['gain_per_sell']:
                    h_metrics['gain_per_sell'][t.id] = h_metrics['realized_gain']
                    last_realized_gain = h_metrics['realized_gain']
                else:
                    value = h_metrics['realized_gain'] - last_realized_gain
                    h_metrics['gain_per_sell'][t.id] = value
                    last_realized_gain = h_metrics['realized_gain']

                # terminar el bucle cuando se haya cubrido la ventas con los lotes
                break

    h_metrics['current_invested'] = sum([lots['shares'] * lots['price_per_share'] for lots in h_metrics['lots']])

    # calcelo de métricas que dependen de la inversión actual
    if h_metrics['current_invested'] > 0:

        h_metrics['current_invested_value'] = current_price * h_metrics['total_shares']
        h_metrics['unrealized_gain'] = Decimal(h_metrics['current_invested_value'] - h_metrics['current_invested'])
        h_metrics['unrealized_gain_percent'] = (h_metrics['unrealized_gain'] / h_metrics['current_invested']) * 100
    
    h_metrics['total_gain'] = h_metrics['unrealized_gain'] + h_metrics['realized_gain'] + h_metrics['total_dividends']

    return h_metrics

# calcular conversión de usd a dop
def convert_currency(value, currency_rate, currency_code):
    '''Convierte de usd a otra moneda utilizando el valor de cambio
    almacenado en caché o consultándolo en yfinance'''
    
    if not currency_rate:
        try:
            currency_rate = yf.Ticker(currency_code).fast_info["last_price"]
            cache.set(currency_code, currency_rate, 3600)
        except Exception as e:
            currency_rate = 1
            logger.exception(f'Error obteniendo el cambio de monede desde yfinance')
            
    return value * Decimal(currency_rate)

# obtener estado actual del mercado
def get_market_status(request, view_name):
    '''Consula un símbolo de yfinance para obtener el estado
    actual del mercado'''

    try:
        market_state = yf.Ticker('VOO').info.get('marketState')
    except Exception:
        market_state = 'CLOSED'
        logger.exception(f'Error obteniendo marketState para desde yfinance en {view_name}')
        messages.error(request, 'Error obteniendo el estado del mercado.')

    return market_state

# obtener activo
def get_holding(symbol, view_name):
    '''Consultar símbolo en yfinance'''
    try:
        ticker = yf.Ticker(symbol)
        return ticker
    except Exception:
        logger.exception(f'No fue obtener a {symbol} en {view_name}')
        return None