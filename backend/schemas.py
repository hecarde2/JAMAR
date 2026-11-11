"""Modelos de datos expuestos por la API (Pydantic v2)."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


Channel = Literal["web", "telegram", "mobile", "api"]


class Product(BaseModel):
    """Producto normalizado para el frontend, el bot y la Mini App."""

    id: str
    sku: str
    name: str
    category: str
    subcategory: str = ""
    color: str = ""
    color_hex: str = "#B9B4A8"
    price: int
    currency: str = "COP"
    width_cm: int = 0
    depth_cm: int = 0
    height_cm: int = 0
    dimensions: str = ""
    material: str = ""
    description: str = ""
    image: str = "sofa.png"
    rating: float = 4.5
    tags: List[str] = Field(default_factory=list)
    stock: int = 0
    city: Optional[str] = None
    stock_by_city: Dict[str, int] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    """Mensaje entrante al agente omnicanal."""

    message: str = Field(min_length=1, max_length=2000)
    session_id: Optional[str] = Field(default=None, max_length=128)
    user_id: Optional[str] = Field(default=None, max_length=128)
    channel: Channel = "web"
    city: Optional[str] = Field(default=None, max_length=80)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        return value.strip()


class CreditSimulationRequest(BaseModel):
    """Solicitud de simulación o pre-aprobación CrediJamar."""

    price: float = Field(gt=0, le=100_000_000)
    down_payment: float = Field(default=0, ge=0, le=100_000_000)
    term_weeks: int = Field(default=24, ge=4, le=104)
    user_id: Optional[str] = None
    product_id: Optional[str] = None
    city: Optional[str] = None


class CreditOffer(BaseModel):
    """Resultado de la evaluación CrediJamar."""

    approved: bool
    status: str
    approved_amount: int
    max_amount: int
    price: int
    down_payment: int
    financed_amount: int
    term_weeks: int
    weekly_rate: float
    weekly_payment: int
    monthly_payment: int
    total_interest: int
    total_to_pay: int
    annual_effective_rate: float
    credit_score: int
    customer_name: str
    reason: str
    disclaimer: str = (
        "Simulación informativa. La aprobación definitiva se confirma al completar "
        "la solicitud con un asesor CrediJamar."
    )


class VisionAnalysis(BaseModel):
    """Hallazgos del análisis visual del espacio."""

    room_type: str
    style: str
    dominant_colors: List[str]
    notes: str
    recommended_category: str
    source: str = "heuristic"


class ChatResponse(BaseModel):
    """Respuesta unificada del agente."""

    reply: str
    intent: str
    session_id: str
    products: List[Product] = Field(default_factory=list)
    credit: Optional[CreditOffer] = None
    suggestions: List[str] = Field(default_factory=list)
    source: str = "demo"


class VisionResponse(BaseModel):
    """Respuesta del módulo de visión."""

    analysis: VisionAnalysis
    reply: str
    products: List[Product] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    session_id: str


class InventorySummary(BaseModel):
    """Resumen de inventario agrupado por categoría."""

    total_products: int
    total_units: int
    categories: Dict[str, int]
    cities: List[str]


class HealthResponse(BaseModel):
    """Estado de los servicios del backend."""

    status: str
    version: str
    snowflake_mode: str
    ai_enabled: bool
    telegram_enabled: bool
    timestamp: str


class CustomerProfile(BaseModel):
    """Vista Customer 360 resumida."""

    user_id: str
    name: str
    document: str = ""
    city: str = ""
    segment: str = ""
    purchases: int = 0
    avg_ticket: int = 0
    last_purchase: Optional[str] = None
    preferred_categories: List[str] = Field(default_factory=list)
    monthly_income: int = 0
    monthly_obligations: int = 0
    credit_score: int = 0
    credi_jamar_limit: int = 0
