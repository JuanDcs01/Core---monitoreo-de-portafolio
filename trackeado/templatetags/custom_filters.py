from django import template
import humanize
from django.utils.safestring import mark_safe
from decimal import Decimal
from django.utils.html import format_html
import yfinance as yf
from django.core.cache import cache

register = template.Library()

@register.filter
def holding_type(type):
    if type == 'EQUITY':
        return 'Acción'
    elif type == 'ETF':
        return 'ETF'
    elif type == 'CRYPTOCURRENCY':
        return 'Cripto'

@register.filter
def recommendation(value):

    if value == 'strong_buy':
        return 'Compra fuerte'
    elif value == 'buy':
        return 'Compra'
    elif value == 'hold':
        return 'Mantener'
    elif value == 'sell':
        return 'Vender'
    elif value == 'strong_sell':
        return 'Venta fuerte'

@register.filter
def metric(data):

    return humanize.metric(data)

@register.filter
def market_state(value):

    if value in ['POST', 'POSTPOST', 'PREPRE']:
        return mark_safe('<i class="bi bi-moon-stars-fill text-primary"></i> Post-mercado')
    if value == 'PRE':
        return mark_safe('<i class="bi bi-brightness-alt-high-fill text-warning"></i> Pre-mercado')
    if value == 'REGULAR':
        return mark_safe('<i class="bi bi-brightness-high-fill"></i> Mercado abierto')

    return ''

@register.filter
def round_number(value):

    if not value:
        return '0.00'

    return round(Decimal(value), 2)

@register.filter
def no_trailing_zeros(value):

    if not value:
        return '0.00'

    if Decimal(value) < 1e-15:
        return '0.00'

    value = str(value)

    point = value.find('.')

    if point == -1:
        return value

    int = value[:point]
    decimal = value[point + 1:][:16]
    
    for x in range(len(decimal) -1, -1, -1):

        if decimal[x] != '0':
            return int + '.' + decimal[:x + 1]

    return value

@register.filter
def identify_transaction(value):

    if value in ['Compra', 'Depósito']:
        return format_html('''<div style="background-color: green; color: white; border: 1px solid green; border-radius: 5px;
        padding: 0px 6px; display: inline-block">{}</div>''', value)

    if value in ['Venta', 'Retiro']:
        return format_html('''<div style="background-color: red; color: white; border: 1px solid red; border-radius: 5px;
        padding: 0px 6px; display: inline-block">{}</div>''', value)

    return value

@register.filter
def is_reinvested(value):
    if value == True:
        return mark_safe('<i class="bi bi-check-lg text-success"></i>')
    else:
        return mark_safe('<i class="bi bi-x-lg text-danger"></i>')

@register.filter
def to_dop(value):
    dop_currency = cache.get('dop_price')
    
    if not dop_currency:
        try:
            ticker = yf.Ticker("USDDOP=X")
            dop_currency = ticker.fast_info["last_price"]
            cache.set('dop_price', dop_currency, 3600)
        except Exception:
            dop_currency = 60.0

    return value * Decimal(dop_currency)

@register.filter
def sector_es(value):
    # Mapeo completo de Sectores e Industrias de Yahoo Finance / yfinance a Español

    SECTOR_ES = {
        'Communication Services': 'Servicios de Comunicación',
        'Technology': 'Tecnología',
        'Financial Services': 'Servicios Financieros',
        'Healthcare': 'Salud y Farmacia',
        'Consumer Cyclical': 'Consumo Cíclico / Discrecional',
        'Consumer Defensive': 'Consumo Defensivo / Básico',
        'Industrials': 'Industrial',
        'Energy': 'Energía',
        'Basic Materials': 'Materiales Básicos',
        'Real Estate': 'Bienes Raíces / Inmobiliario',
        'Utilities': 'Servicios Públicos'
    }

    return SECTOR_ES.get(value)

@register.filter
def industry_es(value):
    INDUSTRY_ES = {
        # --- Communication Services ---
        'Advertising Agencies': 'Agencias de Publicidad',
        'Broadcasting': 'Radiodifusión y Medios',
        'Electronic Gaming & Multimedia': 'Videojuegos y Entretenimiento Multimedia',
        'Entertainment': 'Entretenimiento',
        'Internet Content & Information': 'Contenido e Información de Internet',
        'Publishing': 'Editorial y Publicaciones',
        'Telecom Services': 'Servicios de Telecomunicaciones',

        # --- Technology ---
        'Communication Equipment': 'Equipos de Comunicación',
        'Computer Hardware': 'Hardware Informático',
        'Consumer Electronics': 'Electrónica de Consumo',
        'Electronic Components': 'Componentes Electrónicos',
        'Electronics & Computer Distribution': 'Distribución de Electrónica e Informática',
        'Information Technology Services': 'Servicios de Tecnologías de la Información (TI)',
        'Scientific & Technical Instruments': 'Instrumentos Científicos y Técnicos',
        'Semiconductor Equipment & Materials': 'Equipos y Materiales de Semiconductores',
        'Semiconductors': 'Semiconductores',
        'Software - Application': 'Software de Aplicación',
        'Software - Infrastructure': 'Software de Infraestructura',

        # --- Financial Services ---
        'Asset Management': 'Gestión de Activos y Fondos',
        'Banks - Diversified': 'Banca Diversificada',
        'Banks - Regional': 'Banca Regional',
        'Capital Markets': 'Mercados de Capitales',
        'Credit Services': 'Servicios de Crédito y Financiación',
        'Financial Conglomerates': 'Conglomerados Financieros',
        'Financial Data & Stock Exchanges': 'Datos Financieros y Bolsas de Valores',
        'Insurance Brokers': 'Corredores de Seguros',
        'Insurance - Diversified': 'Seguros Diversificados',
        'Insurance - Life': 'Seguros de Vida',
        'Insurance - Property & Casualty': 'Seguros Generales y de Accidentes',
        'Insurance - Reinsurance': 'Reaseguros',
        'Insurance - Specialty': 'Seguros Especializados',
        'Mortgage Finance': 'Financiación Hipotecaria',

        # --- Healthcare ---
        'Biotechnology': 'Biotecnología',
        'Diagnostics & Research': 'Diagnóstico e Investigación Clínica',
        'Drug Manufacturers - General': 'Fabricantes Farmacéuticos Generales',
        'Drug Manufacturers - Specialty & Generic': 'Medicamentos Especializados y Genéricos',
        'Health Information Services': 'Servicios de Información Sanitaria',
        'Healthcare Plans': 'Planes y Seguros de Salud',
        'Medical Care Facilities': 'Centros e Instalaciones de Atención Médica',
        'Medical Devices': 'Dispositivos Médicos',
        'Medical Distribution': 'Distribución Médica y Farmacéutica',
        'Medical Instruments & Supplies': 'Instrumentos y Suministros Médicos',
        'Pharmaceutical Retailers': 'Farmacias y Minoristas Farmacéuticos',

        # --- Consumer Cyclical ---
        'Apparel Manufacturing': 'Fabricación de Ropa y Confección',
        'Apparel Retail': 'Venta Minorista de Ropa y Moda',
        'Auto & Truck Dealerships': 'Concesionarios de Automóviles y Camiones',
        'Auto Manufacturers': 'Fabricantes de Automóviles',
        'Auto Parts': 'Autopartes y Componentes',
        'Department Stores': 'Grandes Almacenes',
        'Footwear & Accessories': 'Calzado y Accesorios',
        'Furnishings, Fixtures & Appliances': 'Muebles, Accesorios y Electrodomésticos',
        'Gambling': 'Juegos de Azar y Apuestas',
        'Home Improvement Retail': 'Mejoras para el Hogar y Bricolaje',
        'Internet Retail': 'Comercio Electrónico / Venta Minorista Online',
        'Leisure': 'Ocio y Recreación',
        'Lodging': 'Hotelería y Alojamiento',
        'Luxury Goods': 'Artículos de Lujo',
        'Packaging & Containers': 'Envases y Embalajes',
        'Personal Services': 'Servicios Personales',
        'Recreational Vehicles': 'Vehículos Recreativos',
        'Residential Construction': 'Construcción Residencial',
        'Resorts & Casinos': 'Centros Turísticos y Casinos',
        'Restaurants': 'Restaurantes',
        'Specialty Retail': 'Venta Minorista Especializada',
        'Textile Manufacturing': 'Fabricación Textil',
        'Travel Services': 'Servicios de Viajes y Turismo',

        # --- Consumer Defensive ---
        'Beverages - Brewers': 'Bebidas - Cerveceras',
        'Beverages - Non-Alcoholic': 'Bebidas No Alcohólicas',
        'Beverages - Wineries & Distilleries': 'Bebidas - Bodegas y Destilerías',
        'Confectioners': 'Confitería y Dulces',
        'Discount Stores': 'Tiendas de Descuento',
        'Education & Training Services': 'Servicios de Educación y Capacitación',
        'Farm Products': 'Productos Agrícolas y Granja',
        'Food Distribution': 'Distribución de Alimentos',
        'Grocery Stores': 'Supermercados y Tiendas de Comestibles',
        'Household & Personal Products': 'Productos para el Hogar y Cuidado Personal',
        'Packaged Foods': 'Alimentos Envasados y Procesados',
        'Tobacco': 'Tabaco y Derivados',

        # --- Industrials ---
        'Aerospace & Defense': 'Aeroespacial y Defensa',
        'Airlines': 'Aerolíneas',
        'Airports & Air Services': 'Aeropuertos y Servicios Aéreos',
        'Building Products & Equipment': 'Materiales y Equipos de Construcción',
        'Business Equipment & Supplies': 'Equipos y Suministros para Oficinas/Empresas',
        'Conglomerates': 'Conglomerados Industriales',
        'Consulting Services': 'Servicios de Consultoría',
        'Electrical Equipment & Parts': 'Equipos y Componentes Eléctricos',
        'Engineering & Construction': 'Ingeniería y Construcción',
        'Farm & Heavy Construction Machinery': 'Maquinaria Agrícola y de Construcción Pesada',
        'Industrial Distribution': 'Distribución Industrial',
        'Infrastructure Operations': 'Operaciones de Infraestructura',
        'Integrated Freight & Logistics': 'Transporte de Carga y Logística Integrada',
        'Marine Shipping': 'Transporte Marítimo y Naviero',
        'Metal Fabrication': 'Fabricación y Estructuras Metálicas',
        'Pollution & Treatment Controls': 'Control de Contaminación y Tratamiento',
        'Railroads': 'Ferrocarriles y Transporte Ferroviario',
        'Rental & Leasing Services': 'Servicios de Alquiler y Leasing',
        'Security & Protection Services': 'Servicios de Seguridad y Protección',
        'Specialty Business Services': 'Servicios Empresariales Especializados',
        'Specialty Industrial Machinery': 'Maquinaria Industrial Especializada',
        'Staffing & Employment Services': 'Servicios de Empleo y Recursos Humanos',
        'Tools & Accessories': 'Herramientas y Accesorios',
        'Trucking': 'Transporte Terrestre por Camión',
        'Waste Management': 'Gestión y Tratamiento de Residuos',

        # --- Energy ---
        'Oil & Gas Drilling': 'Perforación de Petróleo y Gas',
        'Oil & Gas E&P': 'Exploración y Producción de Petróleo y Gas (E&P)',
        'Oil & Gas Equipment & Services': 'Equipos y Servicios para Petróleo y Gas',
        'Oil & Gas Integrated': 'Petróleo y Gas Integrado',
        'Oil & Gas Midstream': 'Transporte y Almacenamiento de Hidrocarburos (Midstream)',
        'Oil & Gas Refining & Marketing': 'Refinación y Comercialización de Petróleo y Gas',
        'Thermal Coal': 'Carbón Térmico',
        'Uranium': 'Uranio y Combustibles Nucleares',

        # --- Basic Materials ---
        'Agricultural Inputs': 'Insumos y Fertilizantes Agrícolas',
        'Aluminum': 'Aluminio',
        'Building Materials': 'Materiales de Construcción Básicos',
        'Chemicals': 'Productos Químicos Generales',
        'Coking Coal': 'Carbón Coque / Metalúrgico',
        'Copper': 'Cobre',
        'Gold': 'Oro',
        'Lumber & Wood Production': 'Madera y Producción Forestal',
        'Other Industrial Metals & Mining': 'Otros Metales Industriales y Minería',
        'Other Precious Metals & Mining': 'Otros Metales Preciosos y Minería',
        'Paper & Paper Products': 'Papel y Productos Derivados',
        'Silver': 'Plata',
        'Specialty Chemicals': 'Química Especializada',
        'Steel': 'Acero y Siderurgia',

        # --- Real Estate ---
        'Real Estate Services': 'Servicios Inmobiliarios',
        'Real Estate - Development': 'Desarrollo y Promoción Inmobiliaria',
        'Real Estate - Diversified': 'Inmobiliario Diversificado',
        'REIT - Diversified': 'REIT (FIBRAS) - Diversificados',
        'REIT - Healthcare Facilities': 'REIT (FIBRAS) - Instalaciones Sanitarias',
        'REIT - Hotel & Motel': 'REIT (FIBRAS) - Hoteles y Alojamiento',
        'REIT - Industrial': 'REIT (FIBRAS) - Naves y Logística Industrial',
        'REIT - Mortgage': 'REIT (FIBRAS) - Hipotecarios',
        'REIT - Office': 'REIT (FIBRAS) - Oficinas',
        'REIT - Residential': 'REIT (FIBRAS) - Residenciales',
        'REIT - Retail': 'REIT (FIBRAS) - Centros Comerciales y Minoristas',
        'REIT - Specialty': 'REIT (FIBRAS) - Especializados (Torres, Data Centers)',

        # --- Utilities ---
        'Utilities - Diversified': 'Servicios Públicos Diversificados',
        'Utilities - Independent Power Producers': 'Productores Independientes de Energía',
        'Utilities - Regulated Electric': 'Electricidad Regulada',
        'Utilities - Regulated Gas': 'Gas Regulado',
        'Utilities - Regulated Water': 'Agua y Saneamiento Regulado',
        'Utilities - Renewable': 'Energías Renovables y Limpias'
    }

    return INDUSTRY_ES.get(value)

@register.filter
def number_format_es(valor: float | int, decimales: int = 2) -> str:
    """
    Formatea números grandes al estándar financiero habitual:
    - Miles: 'mil' o 'k'
    - Millones: 'M'
    - Miles de millones (Billions en inglés): 'Mil M' o 'B'
    - Billones en español (Trillions en inglés): 'Bln' o 'T'
    """
    if valor is None:
        return "N/A"
    
    signo = "-" if valor < 0 else ""
    n = abs(float(valor))

    if n >= 1e12:
        return f"{signo}{n / 1e12:.{decimales}f} T"      # o 'Bln' en escala larga española
    elif n >= 1e9:
        return f"{signo}{n / 1e9:.{decimales}f} Mil M"  # o 'B' si prefieres la convención bursátil
    elif n >= 1e6:
        return f"{signo}{n / 1e6:.{decimales}f} M"
    elif n >= 1e3:
        return f"{signo}{n / 1e3:.{decimales}f} mil"
    else:
        return f"{signo}{n:.{decimales}f}"