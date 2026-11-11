"""Catálogo semilla y datos de demostración.

El backend funciona en dos modos:
1. Snowflake: cuando las credenciales están configuradas se consulta el data warehouse.
2. Demostración: si no hay credenciales (o si la consulta falla) se usa este catálogo
   verosímil para que el widget, el bot y la Mini App sean completamente operativos.

La estructura de cada producto replica las columnas esperadas en `INVENTARIO_PRODUCTOS`.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List

CITIES: List[Dict[str, Any]] = [
    {"name": "Bogotá", "stores": 12, "delivery_days": 1},
    {"name": "Medellín", "stores": 8, "delivery_days": 1},
    {"name": "Cali", "stores": 6, "delivery_days": 2},
    {"name": "Barranquilla", "stores": 5, "delivery_days": 2},
    {"name": "Cartagena", "stores": 3, "delivery_days": 3},
    {"name": "Bucaramanga", "stores": 3, "delivery_days": 3},
]

CITY_NAMES = [city["name"] for city in CITIES]

# Categorías reconocidas por el clasificador de intenciones.
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "Sala": ["sala", "sofa", "sofá", "sofas", "sofás", "butaca", "sillón", "sillon", "mueble de sala"],
    "Comedor": ["comedor", "mesa de comedor", "sillas de comedor", "comedores"],
    "Alcoba": ["alcoba", "cama", "habitación", "habitacion", "dormitorio", "nochero", "colchón", "colchon"],
    "Almacenamiento": ["closet", "clóset", "armario", "biblioteca", "almacenamiento", "organizador"],
    "Oficina": ["oficina", "escritorio", "silla ergonómica", "silla ergonomica", "home office", "estudio"],
}

COLOR_KEYWORDS: Dict[str, str] = {
    "gris": "#8A8D8F",
    "beige": "#CDBBA2",
    "verde": "#3F6B52",
    "blanco": "#EDEAE4",
    "negro": "#2B2B2B",
    "nogal": "#7A4E2D",
    "miel": "#B07A3F",
    "azul": "#3A5A78",
    "madera": "#8B5E3C",
    "crema": "#E8DFCE",
}


def _stock(**values: int) -> Dict[str, int]:
    """Normaliza el inventario por ciudad."""
    return {city: int(values.get(city, 0)) for city in CITY_NAMES}


DEMO_PRODUCTS: List[Dict[str, Any]] = [
    {
        "id": "JAM-SAL-001",
        "sku": "SAL-MIA-3P-GR",
        "name": "Sofá Miami 3 puestos",
        "category": "Sala",
        "subcategory": "Sofás",
        "color": "Gris",
        "color_hex": "#8A8D8F",
        "price": 2_899_000,
        "width_cm": 210,
        "depth_cm": 92,
        "height_cm": 88,
        "material": "Tela antimanchas, estructura en madera",
        "description": "Sofá familiar de líneas rectas con cojines de alta densidad. Ideal para espacios de 18 a 25 m2.",
        "image": "sofa.png",
        "rating": 4.7,
        "tags": ["moderno", "familiar", "tres puestos", "tela"],
        "stock_by_city": _stock(Bogotá=14, Medellín=9, Cali=6, Barranquilla=4, Cartagena=3, Bucaramanga=2),
    },
    {
        "id": "JAM-SAL-002",
        "sku": "SAL-ARI-MOD-BE",
        "name": "Sofá modular Aria",
        "category": "Sala",
        "subcategory": "Sofás",
        "color": "Beige",
        "color_hex": "#CDBBA2",
        "price": 3_649_000,
        "width_cm": 260,
        "depth_cm": 100,
        "height_cm": 85,
        "material": "Lino tratado, espuma de alta resiliencia",
        "description": "Módulos configurables que se adaptan a salas amplias y apartamentos con iluminación natural.",
        "image": "sofa.png",
        "rating": 4.8,
        "tags": ["modular", "premium", "amplio", "lino"],
        "stock_by_city": _stock(Bogotá=8, Medellín=6, Cali=3, Barranquilla=2, Cartagena=2, Bucaramanga=1),
    },
    {
        "id": "JAM-SAL-003",
        "sku": "SAL-OSL-BUT-VE",
        "name": "Butaca Nórdica Oslo",
        "category": "Sala",
        "subcategory": "Butacas",
        "color": "Verde",
        "color_hex": "#3F6B52",
        "price": 899_000,
        "width_cm": 78,
        "depth_cm": 80,
        "height_cm": 85,
        "material": "Tela bouclé, patas en madera de fresno",
        "description": "Butaca compacta de acento para leer o complementar la sala. Aporta color sin recargar el espacio.",
        "image": "butaca.png",
        "rating": 4.6,
        "tags": ["compacto", "acento", "nórdico", "bouclé"],
        "stock_by_city": _stock(Bogotá=22, Medellín=15, Cali=11, Barranquilla=7, Cartagena=5, Bucaramanga=6),
    },
    {
        "id": "JAM-SAL-004",
        "sku": "SAL-ROB-MC-MI",
        "name": "Mesa de centro Roble",
        "category": "Sala",
        "subcategory": "Mesas de centro",
        "color": "Miel",
        "color_hex": "#B07A3F",
        "price": 749_000,
        "width_cm": 110,
        "depth_cm": 60,
        "height_cm": 40,
        "material": "Madera de roble con acabado mate",
        "description": "Mesa de centro de proporciones equilibradas, con compartimento inferior para revistas.",
        "image": "mesa.png",
        "rating": 4.5,
        "tags": ["madera", "centro", "minimalista"],
        "stock_by_city": _stock(Bogotá=18, Medellín=13, Cali=9, Barranquilla=5, Cartagena=4, Bucaramanga=7),
    },
    {
        "id": "JAM-COM-001",
        "sku": "COM-BER-6P-NO",
        "name": "Comedor Escandinavo Bergen 6 puestos",
        "category": "Comedor",
        "subcategory": "Comedores",
        "color": "Nogal",
        "color_hex": "#7A4E2D",
        "price": 3_299_000,
        "width_cm": 180,
        "depth_cm": 90,
        "height_cm": 75,
        "material": "Madera de nogal y sillas tapizadas",
        "description": "Juego de comedor para seis personas con mesa de canto recto y sillas de respaldo curvo.",
        "image": "comedor.png",
        "rating": 4.8,
        "tags": ["seis puestos", "madera", "escandinavo", "familiar"],
        "stock_by_city": _stock(Bogotá=7, Medellín=5, Cali=4, Barranquilla=3, Cartagena=1, Bucaramanga=2),
    },
    {
        "id": "JAM-COM-002",
        "sku": "COM-VAN-4P-BL",
        "name": "Comedor Vancouver 4 puestos",
        "category": "Comedor",
        "subcategory": "Comedores",
        "color": "Blanco",
        "color_hex": "#EDEAE4",
        "price": 2_199_000,
        "width_cm": 140,
        "depth_cm": 85,
        "height_cm": 76,
        "material": "MDF lacado y sillas en madera",
        "description": "Comedor compacto para apartamentos. Superficie fácil de limpiar y sillas livianas.",
        "image": "comedor.png",
        "rating": 4.4,
        "tags": ["cuatro puestos", "compacto", "apartamento", "blanco"],
        "stock_by_city": _stock(Bogotá=16, Medellín=12, Cali=8, Barranquilla=6, Cartagena=4, Bucaramanga=5),
    },
    {
        "id": "JAM-COM-003",
        "sku": "COM-COP-SIL-GR",
        "name": "Silla Copenhagen",
        "category": "Comedor",
        "subcategory": "Sillas",
        "color": "Gris",
        "color_hex": "#8A8D8F",
        "price": 449_000,
        "width_cm": 48,
        "depth_cm": 54,
        "height_cm": 82,
        "material": "Tapizado en tela y estructura metálica",
        "description": "Silla versátil de uso diario, apilable y con tapizado de secado rápido.",
        "image": "silla.png",
        "rating": 4.5,
        "tags": ["apilable", "diario", "comedor"],
        "stock_by_city": _stock(Bogotá=40, Medellín=28, Cali=20, Barranquilla=15, Cartagena=9, Bucaramanga=12),
    },
    {
        "id": "JAM-ALC-001",
        "sku": "ALC-URI-QUE-GR",
        "name": "Cama Uribe Queen",
        "category": "Alcoba",
        "subcategory": "Camas",
        "color": "Gris",
        "color_hex": "#8A8D8F",
        "price": 2_549_000,
        "width_cm": 166,
        "depth_cm": 210,
        "height_cm": 100,
        "material": "Tapizado en tela, base en madera",
        "description": "Cama queen con cabecera tapizada y espacio de almacenamiento inferior. Medida colchón 160 x 190 cm.",
        "image": "cama.png",
        "rating": 4.7,
        "tags": ["queen", "almacenamiento", "tapizada"],
        "stock_by_city": _stock(Bogotá=10, Medellín=8, Cali=5, Barranquilla=4, Cartagena=2, Bucaramanga=3),
    },
    {
        "id": "JAM-ALC-002",
        "sku": "ALC-MAD-KIN-BE",
        "name": "Cama Madrid King",
        "category": "Alcoba",
        "subcategory": "Camas",
        "color": "Beige",
        "color_hex": "#CDBBA2",
        "price": 3_499_000,
        "width_cm": 200,
        "depth_cm": 215,
        "height_cm": 110,
        "material": "Tapizado premium, patas metálicas",
        "description": "Cama king con cabecera de líneas suaves y refuerzo central. Medida colchón 200 x 200 cm.",
        "image": "cama.png",
        "rating": 4.9,
        "tags": ["king", "premium", "dormitorio principal"],
        "stock_by_city": _stock(Bogotá=5, Medellín=4, Cali=3, Barranquilla=2, Cartagena=1, Bucaramanga=1),
    },
    {
        "id": "JAM-ALC-003",
        "sku": "ALC-LUN-NOC-BL",
        "name": "Nochero Luna",
        "category": "Alcoba",
        "subcategory": "Nocheros",
        "color": "Blanco",
        "color_hex": "#EDEAE4",
        "price": 399_000,
        "width_cm": 50,
        "depth_cm": 40,
        "height_cm": 55,
        "material": "MDF lacado con tiradores metálicos",
        "description": "Nochero de dos cajones con acabado mate y líneas limpias para dormitorios contemporáneos.",
        "image": "almacenamiento.png",
        "rating": 4.3,
        "tags": ["nochero", "dos cajones", "blanco"],
        "stock_by_city": _stock(Bogotá=26, Medellín=18, Cali=14, Barranquilla=10, Cartagena=6, Bucaramanga=8),
    },
    {
        "id": "JAM-ALM-001",
        "sku": "ALM-PRA-CLO-BL",
        "name": "Closet Praga 6 puertas",
        "category": "Almacenamiento",
        "subcategory": "Closets",
        "color": "Blanco",
        "color_hex": "#EDEAE4",
        "price": 2_899_000,
        "width_cm": 240,
        "depth_cm": 60,
        "height_cm": 220,
        "material": "MDF con recubrimiento melamínico",
        "description": "Closet de seis puertas con divisiones internas, barra para colgar y cajonera central.",
        "image": "closet.png",
        "rating": 4.6,
        "tags": ["seis puertas", "organización", "dormitorio"],
        "stock_by_city": _stock(Bogotá=9, Medellín=7, Cali=5, Barranquilla=3, Cartagena=2, Bucaramanga=2),
    },
    {
        "id": "JAM-ALM-002",
        "sku": "ALM-VER-BIB-MI",
        "name": "Biblioteca Verona",
        "category": "Almacenamiento",
        "subcategory": "Bibliotecas",
        "color": "Miel",
        "color_hex": "#B07A3F",
        "price": 1_449_000,
        "width_cm": 120,
        "depth_cm": 35,
        "height_cm": 180,
        "material": "Madera engineered con acabado miel",
        "description": "Biblioteca de cinco niveles con estructura abierta, ideal para sala o estudio.",
        "image": "biblioteca.png",
        "rating": 4.5,
        "tags": ["cinco niveles", "sala", "estudio"],
        "stock_by_city": _stock(Bogotá=15, Medellín=11, Cali=8, Barranquilla=5, Cartagena=4, Bucaramanga=6),
    },
    {
        "id": "JAM-OFI-001",
        "sku": "OFI-NOR-ESC-NO",
        "name": "Escritorio Nordic",
        "category": "Oficina",
        "subcategory": "Escritorios",
        "color": "Nogal",
        "color_hex": "#7A4E2D",
        "price": 999_000,
        "width_cm": 120,
        "depth_cm": 60,
        "height_cm": 75,
        "material": "Madera de nogal y acero negro",
        "description": "Escritorio de trabajo con pasacables y estructura metálica. Recomendado para home office.",
        "image": "escritorio.png",
        "rating": 4.7,
        "tags": ["home office", "pasacables", "compacto"],
        "stock_by_city": _stock(Bogotá=19, Medellín=14, Cali=10, Barranquilla=7, Cartagena=5, Bucaramanga=6),
    },
    {
        "id": "JAM-OFI-002",
        "sku": "OFI-FLX-SIL-NE",
        "name": "Silla Ergonómica Flux",
        "category": "Oficina",
        "subcategory": "Sillas",
        "color": "Negro",
        "color_hex": "#2B2B2B",
        "price": 1_199_000,
        "width_cm": 65,
        "depth_cm": 65,
        "height_cm": 115,
        "material": "Malla transpirable y base de nylon reforzado",
        "description": "Silla ergonómica con soporte lumbar ajustable, apoyabrazos y regulación de altura.",
        "image": "silla.png",
        "rating": 4.8,
        "tags": ["ergonómica", "soporte lumbar", "oficina"],
        "stock_by_city": _stock(Bogotá=12, Medellín=9, Cali=7, Barranquilla=4, Cartagena=3, Bucaramanga=4),
    },
]

# Clientes de demostración para Customer 360 y pre-aprobación CrediJamar.
DEMO_CUSTOMERS: Dict[str, Dict[str, Any]] = {
    "tg-1001": {
        "user_id": "tg-1001",
        "name": "Laura Gómez",
        "document": "****4821",
        "city": "Bogotá",
        "segment": "Hogar consolidado",
        "purchases": 7,
        "avg_ticket": 1_850_000,
        "last_purchase": "2026-08-14",
        "preferred_categories": ["Sala", "Alcoba"],
        "monthly_income": 4_800_000,
        "monthly_obligations": 420_000,
        "credit_score": 762,
        "credi_jamar_limit": 6_500_000,
    },
    "demo-user": {
        "user_id": "demo-user",
        "name": "Cliente Jamar",
        "document": "****0000",
        "city": "Medellín",
        "segment": "Primera compra",
        "purchases": 0,
        "avg_ticket": 0,
        "last_purchase": None,
        "preferred_categories": ["Comedor"],
        "monthly_income": 2_900_000,
        "monthly_obligations": 180_000,
        "credit_score": 688,
        "credi_jamar_limit": 2_400_000,
    },
}

_FIRST_NAMES = ["Andrea", "Carlos", "Diana", "Felipe", "Paula", "Jorge", "Camila", "Andrés", "Natalia", "Santiago"]
_LAST_NAMES = ["Restrepo", "Martínez", "Rodríguez", "Pérez", "Gómez", "Cárdenas", "Vargas", "Moreno", "Rojas", "Silva"]


def demo_customer(user_id: str) -> Dict[str, Any]:
    """Genera un perfil Customer 360 determinista para sesiones no registradas.

    La generación determinista evita que el score o la ciudad cambien entre llamadas,
    manteniendo coherencia durante toda la conversación.
    """
    key = (user_id or "demo-user").lower()
    if key in DEMO_CUSTOMERS:
        return dict(DEMO_CUSTOMERS[key])

    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16)
    score = 640 + (idx % 150)
    city = CITY_NAMES[idx % len(CITY_NAMES)]
    income = 2_200_000 + (idx % 12) * 250_000
    obligations = 120_000 + (idx % 7) * 60_000
    purchases = idx % 6
    return {
        "user_id": user_id,
        "name": f"{_FIRST_NAMES[idx % len(_FIRST_NAMES)]} {_LAST_NAMES[(idx // 7) % len(_LAST_NAMES)]}",
        "document": f"****{1000 + (idx % 8999)}",
        "city": city,
        "segment": "Hogar" if purchases else "Primera compra",
        "purchases": purchases,
        "avg_ticket": 950_000 + (idx % 9) * 120_000 if purchases else 0,
        "last_purchase": "2026-06-30" if purchases else None,
        "preferred_categories": [["Sala", "Comedor", "Alcoba", "Oficina"][idx % 4]],
        "monthly_income": income,
        "monthly_obligations": obligations,
        "credit_score": score,
        "credi_jamar_limit": credit_limit_for_score(score),
    }


def credit_limit_for_score(score: int) -> int:
    """Cupo máximo precargado según el score de crédito."""
    if score >= 750:
        return 8_000_000
    if score >= 700:
        return 5_000_000
    if score >= 650:
        return 3_000_000
    if score >= 600:
        return 1_800_000
    return 800_000


def public_product(product: Dict[str, Any], city: str | None = None) -> Dict[str, Any]:
    """Convierte un registro interno en la estructura pública de producto."""
    stock_by_city = product.get("stock_by_city", {}) or {}
    if city and city in stock_by_city:
        stock = int(stock_by_city[city])
    else:
        stock = sum(int(value) for value in stock_by_city.values())

    return {
        "id": product["id"],
        "sku": product.get("sku", product["id"]),
        "name": product["name"],
        "category": product.get("category", ""),
        "subcategory": product.get("subcategory", ""),
        "color": product.get("color", ""),
        "color_hex": product.get("color_hex", "#B9B4A8"),
        "price": int(product.get("price", 0)),
        "currency": "COP",
        "width_cm": int(product.get("width_cm", 0) or 0),
        "depth_cm": int(product.get("depth_cm", 0) or 0),
        "height_cm": int(product.get("height_cm", 0) or 0),
        "dimensions": (
            f"{int(product.get('width_cm', 0) or 0)} x "
            f"{int(product.get('depth_cm', 0) or 0)} x "
            f"{int(product.get('height_cm', 0) or 0)} cm"
        ),
        "material": product.get("material", ""),
        "description": product.get("description", ""),
        "image": product.get("image", "sofa.png"),
        "rating": float(product.get("rating", 4.5)),
        "tags": product.get("tags", []),
        "stock": stock,
        "city": city,
        "stock_by_city": stock_by_city,
    }
