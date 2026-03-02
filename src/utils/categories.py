"""Category management utilities."""

# Categorization keywords map
CATEGORIES = {
    "💳 Pago Tarjeta Crédito": ["transfer to card", "traspaso a tarjeta", "pago tarjeta", "adeudo mensual de tarjeta"],
    "💰 Ingreso": ["transfer received", "transferencia recibida", "nómina", "nomina", "salary", "payroll"],
    "📊 Pago Deuda": ["amortizacion de prestamo", "loan payment", "adeudo bmw bank", "adeudo cofidis", "préstamo", "prestamo"],
    "🔄 Transferencia Interna": ["transfer - set up your account", "traspaso programa tu cuenta", "traspaso desde cuenta", "traspaso a cuenta", "trp redondeo"],
    "👥 Bizum": ["bizum"],
    "🏠 Vivienda": ["alquiler", "rent", "hipoteca", "mortgage"],
    "⚡ Electricidad": ["luz", "electricity", "endesa", "energia", "energy"],
    "💧 Agua": ["agua", "water"],
    "🔥 Gas": ["gas natural", "gas"],
    "🌐 Internet": ["internet", "vodafone", "movistar", "orange", "telecomunicaciones"],
    "🛡️ Seguros": ["seguro", "insurance"],
    "🛒 Supermercado": ["mercadona", "carrefour", "dia", "lidl", "aldi", "ahorramas", "eroski"],
    "🍔 Comida a Domicilio": ["glovo", "uber eats", "just eat", "deliveroo"],
    "🍽️ Restaurantes y Ocio": ["restaurante", "restaurant", "bar ", "cafeteria", "cafe ", "mcdonalds", "burger king", "kfc"],
    "⚽ Deporte": ["gimnasio", "gym", "deporte", "sport", "decathlon", "sprinter"],
    "💻 Software y Suscripciones": ["netflix", "spotify", "amazon prime", "google", "apple", "microsoft", "adobe", "subscription"],
    "📦 Amazon": ["amazon"],
    "🛋️ Muebles": ["ikea", "mueble"],
    "🔧 Bricolaje": ["leroy merlin", "bricomart", "bricodepot"],
    "👔 Ropa y Accesorios": ["zara", "h&m", "mango", "pull&bear", "bershka", "stradivarius", "primark"],
    "⛽ Gasolina": ["repsol", "cepsa", "galp", "bp", "shell", "gasolina", "gasolinera"],
    "🅿️ Parking": ["parking", "aparcamiento"],
    "🚕 Taxi/Uber": ["taxi", "uber", "cabify"],
    "🚌 Transporte Público": ["metro", "renfe", "bus", "emt", "transporte"],
    "💊 Farmacia": ["farmacia", "pharmacy"],
    "💇 Peluquería": ["peluqueria", "salon"],
    "💳 PayPal": ["paypal"],
    "💳 Pago con Tarjeta": ["card payment", "pago con tarjeta"],
    "❓ Otros": [],  # Default fallback
}

def get_default_category(text: str) -> str:
    """
    Get default category for a transaction based on text matching.

    Args:
        text: Transaction concept/description text

    Returns:
        Category name (defaults to "❓ Otros" if no match)
    """
    if not text:
        return "❓ Otros"

    text_lower = str(text).lower()

    # Check each category's keywords
    for category, keywords in CATEGORIES.items():
        if category == "❓ Otros":
            continue  # Skip default category in search

        for keyword in keywords:
            if keyword in text_lower:
                return category

    return "❓ Otros"

def get_all_categories():
    """Get list of all available categories."""
    return sorted(list(CATEGORIES.keys()))
