"""Agente de IA omnicanal de Muebles Jamar.

El agente combina recuperación determinista de datos (Snowflake / catálogo) con
generación de lenguaje natural de Google Gemini. Si `GEMINI_API_KEY` no está
configurada, o si la llamada al modelo falla, responde con plantillas
profesionales en español. Esto garantiza que el asistente funcione incluso en
modo demostración.

El identificador de sesión se deriva del `user_id` cuando existe, lo que permite
sincronizar el estado entre el widget web, la Mini App y el bot de Telegram.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from catalog import CATEGORY_KEYWORDS, CITY_NAMES, COLOR_KEYWORDS, demo_customer
from config import get_settings
from credit_engine import simulate_credit
from schemas import ChatResponse, CreditOffer, Product
from snowflake_client import SnowflakeClient, get_snowflake_client, normalize_text

logger = logging.getLogger(__name__)

EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\uFE0F\u200D]"
)

CREDIT_KEYWORDS = [
    "credito",
    "crédito",
    "credijamar",
    "financiacion",
    "financiación",
    "financiar",
    "cuota",
    "cuotas",
    "financiera",
    "prestamo",
    "préstamo",
    "aprobacion",
    "aprobación",
]
VISION_KEYWORDS = ["foto", "fotografia", "fotografía", "imagen", "espacio", "analiza", "analizar", "decorar"]
STOCK_KEYWORDS = ["disponible", "disponibilidad", "stock", "inventario", "en tienda", "hay en", "tienen en"]
HUMAN_KEYWORDS = ["asesor", "humano", "persona", "vendedor", "agente real"]
ORDER_KEYWORDS = ["pedido", "rastrear", "rastreo", "envio", "envío", "entrega", "guia", "guía"]
GREETING_KEYWORDS = ["hola", "buenos dias", "buenos días", "buenas tardes", "buenas noches", "hey", "que tal", "qué tal"]
PRODUCT_KEYWORDS = [
    "buscar",
    "busco",
    "quiero",
    "necesito",
    "mueble",
    "sofa",
    "sofá",
    "sala",
    "comedor",
    "cama",
    "alcoba",
    "closet",
    "escritorio",
    "silla",
    "precio",
    "catalogo",
    "catálogo",
    "recomienda",
    "recomendacion",
    "recomendación",
    "opciones",
    "comprar",
]

MONEY_UNITS = {
    "millon": 1_000_000,
    "millones": 1_000_000,
    "m": 1_000_000,
    "mil": 1_000,
    "k": 1_000,
}

PRICE_PATTERNS = [
    re.compile(
        r"(?:presupuesto|hasta|maximo|máximo|menos de|por|de)\s*(?:unos\s*)?\$?\s*"
        r"([\d\.,]+)\s*(millones|millon|mil|k|m)?",
        re.IGNORECASE,
    ),
    re.compile(r"\$\s*([\d\.,]+)\s*(millones|millon|mil|k|m)?", re.IGNORECASE),
    re.compile(r"([\d\.,]+)\s*(millones|millon|mil)\b", re.IGNORECASE),
]


def strip_emojis(text: str) -> str:
    """Elimina emojis para mantener una comunicación corporativa sobria."""
    cleaned = EMOJI_RE.sub("", text or "")
    return re.sub(r"\s{2,}", " ", cleaned).strip()


def format_cop(value: float) -> str:
    """Formatea pesos colombianos sin decimales."""
    return "$ " + f"{int(round(value)):,.0f}".replace(",", ".")


def _to_number(raw: str, unit: Optional[str]) -> Optional[float]:
    """Convierte expresiones coloquiales de dinero a número."""
    raw = (raw or "").strip().replace("$", "").replace(" ", "")
    if not raw:
        return None
    unit = (unit or "").lower()
    try:
        if unit in MONEY_UNITS:
            normalized = raw
            if normalized.count(".") > 1:
                normalized = normalized.replace(".", "")
            normalized = normalized.replace(",", ".")
            value = float(normalized)
            return value * MONEY_UNITS[unit]
        cleaned = raw.replace(".", "").replace(",", "")
        if not cleaned.isdigit():
            return None
        return float(cleaned)
    except ValueError:
        return None


def extract_money(message: str) -> Optional[int]:
    """Extrae el primer monto de dinero detectado en el mensaje."""
    for pattern in PRICE_PATTERNS:
        match = pattern.search(message)
        if match:
            value = _to_number(match.group(1), match.group(2) if match.lastindex and match.lastindex >= 2 else None)
            if value and value >= 50_000:
                return int(round(value))
    return None


def extract_term_weeks(message: str) -> Optional[int]:
    """Interpreta plazos expresados en semanas o meses."""
    normalized = normalize_text(message)
    weeks = re.search(r"(\d{1,2})\s*semanas?", normalized)
    if weeks:
        return max(4, min(int(weeks.group(1)), 104))
    months = re.search(r"(\d{1,2})\s*meses?", normalized)
    if months:
        return max(4, min(int(round(int(months.group(1)) * 52 / 12)), 104))
    return None


def extract_down_payment(message: str) -> Optional[int]:
    """Detecta cuota inicial o abono expresado por el usuario."""
    match = re.search(
        r"(?:cuota inicial|inicial|abono|anticipo)\D{0,15}([\d\.,]+)\s*(millones|millon|mil|k|m)?",
        message,
        re.IGNORECASE,
    )
    if not match:
        return None
    value = _to_number(match.group(1), match.group(2))
    return int(round(value)) if value else None


def extract_dimensions(message: str) -> Tuple[Optional[int], Optional[int]]:
    """Detecta dimensiones en centímetros (ancho y profundidad)."""
    normalized = normalize_text(message).replace(",", ".")
    pair = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:x|por)\s*(\d+(?:\.\d+)?)\s*(cm|centimetros|metros|m)?",
        normalized,
    )
    if pair:
        factor = 100 if pair.group(3) in ("m", "metros") else 1
        return int(float(pair.group(1)) * factor), int(float(pair.group(2)) * factor)
    single = re.search(r"(\d+(?:\.\d+)?)\s*(cm|centimetros|metros|m)\b", normalized)
    if single:
        factor = 100 if single.group(2) in ("m", "metros") else 1
        return int(float(single.group(1)) * factor), None
    return None, None


def extract_entities(message: str) -> Dict[str, Any]:
    """Extrae ciudad, categoría, color, presupuesto y datos de crédito."""
    normalized = normalize_text(message)

    city = next((name for name in CITY_NAMES if normalize_text(name) in normalized), None)

    category = None
    for name, keywords in CATEGORY_KEYWORDS.items():
        if any(normalize_text(keyword) in normalized for keyword in keywords):
            category = name
            break

    color = next((name for name in COLOR_KEYWORDS if normalize_text(name) in normalized), None)
    width, depth = extract_dimensions(message)
    max_price = extract_money(message)

    return {
        "city": city,
        "category": category,
        "color": color,
        "max_price": max_price,
        "term_weeks": extract_term_weeks(message),
        "down_payment": extract_down_payment(message),
        "width_cm": width,
        "depth_cm": depth,
        "mentions_credit": any(normalize_text(word) in normalized for word in CREDIT_KEYWORDS),
        "mentions_vision": any(normalize_text(word) in normalized for word in VISION_KEYWORDS),
        "mentions_stock": any(normalize_text(word) in normalized for word in STOCK_KEYWORDS),
        "mentions_human": any(normalize_text(word) in normalized for word in HUMAN_KEYWORDS),
    }


def _keyword_present(normalized: str, keyword: str) -> bool:
    """Coincidencia por palabra completa para evitar falsos positivos."""
    target = normalize_text(keyword)
    if not target:
        return False
    if " " in target:
        return target in normalized
    return re.search(rf"\b{re.escape(target)}\b", normalized) is not None


def classify_intent(message: str, entities: Dict[str, Any]) -> str:
    """Clasificador de intenciones basado en reglas, rápido y explicable."""
    normalized = normalize_text(message)
    if any(_keyword_present(normalized, word) for word in GREETING_KEYWORDS) and len(normalized.split()) <= 5:
        return "greeting"
    if entities["mentions_vision"]:
        return "vision"
    if entities["mentions_credit"]:
        return "credit"
    if entities["mentions_stock"]:
        return "stock"
    if any(_keyword_present(normalized, word) for word in HUMAN_KEYWORDS):
        return "human_handoff"
    if any(normalize_text(word) in normalized for word in ORDER_KEYWORDS):
        return "order_status"
    if entities["category"] or any(normalize_text(word) in normalized for word in PRODUCT_KEYWORDS):
        return "product_search"
    return "general"


class SessionStore:
    """Historial de conversación en memoria con bloqueo para concurrencia."""

    def __init__(self, max_messages: int = 16) -> None:
        self._sessions: Dict[str, List[Dict[str, str]]] = {}
        self._timestamps: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._max_messages = max_messages

    def resolve_key(self, user_id: Optional[str], session_id: Optional[str]) -> str:
        """El `user_id` manda para compartir estado entre canales."""
        if user_id and user_id.strip():
            return f"user:{user_id.strip()}"
        if session_id and session_id.strip():
            return session_id.strip()[:128]
        return f"web:{uuid.uuid4().hex[:12]}"

    def append(self, key: str, role: str, content: str) -> None:
        with self._lock:
            history = self._sessions.setdefault(key, [])
            history.append({"role": role, "content": content})
            if len(history) > self._max_messages:
                del history[: len(history) - self._max_messages]
            self._timestamps[key] = datetime.now(timezone.utc).isoformat()

    def history(self, key: str) -> List[Dict[str, str]]:
        with self._lock:
            return list(self._sessions.get(key, []))

    def reset(self, key: str) -> None:
        with self._lock:
            self._sessions.pop(key, None)
            self._timestamps.pop(key, None)

    def last_activity(self, key: str) -> Optional[str]:
        with self._lock:
            return self._timestamps.get(key)


class JamarAgent:
    """Orquestador de recuperación, razonamiento y respuesta."""

    def __init__(self, repository: SnowflakeClient) -> None:
        self.repository = repository
        self.settings = get_settings()
        self.sessions = SessionStore()
        self._client = None
        if self.settings.ai_enabled:
            try:
                from google import genai
                from google.genai import types

                self._client = genai.Client(
                    api_key=self.settings.gemini_api_key,
                    http_options=types.HttpOptions(
                        timeout=int(self.settings.gemini_timeout_seconds * 1000)
                    ),
                )
            except Exception:  # pragma: no cover - dependencia o configuración
                logger.exception("No fue posible inicializar el cliente de Gemini")

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def process(
        self,
        message: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        city: Optional[str] = None,
        channel: str = "web",
    ) -> ChatResponse:
        """Procesa un mensaje y devuelve texto, productos, crédito y sugerencias."""
        key = self.sessions.resolve_key(user_id, session_id)
        entities = extract_entities(message)
        intent = classify_intent(message, entities)
        effective_city = city or entities.get("city")

        customer = None
        if user_id or intent == "credit":
            customer = self.repository.get_customer(user_id or f"web-{key.split(':')[-1]}")

        products: List[Dict[str, Any]] = []
        if intent in {"product_search", "stock", "credit", "general", "greeting"}:
            products = self._retrieve_products(message, entities, effective_city)
        if intent == "vision":
            products = self._retrieve_products(message, entities, effective_city)

        credit_offer: Optional[CreditOffer] = None
        if entities.get("mentions_credit") or intent == "credit":
            credit_offer = self._build_credit_offer(entities, products, customer)

        if self._client is not None:
            reply = self._llm_reply(
                message=message,
                intent=intent,
                entities=entities,
                products=products,
                credit_offer=credit_offer,
                customer=customer,
                key=key,
                city=effective_city,
            )
            source = "gemini"
            if not reply:
                reply = self._fallback_reply(intent, entities, products, credit_offer, customer, effective_city)
                source = "demo"
        else:
            reply = self._fallback_reply(intent, entities, products, credit_offer, customer, effective_city)
            source = "demo"

        reply = strip_emojis(reply)
        self.sessions.append(key, "user", message)
        self.sessions.append(key, "assistant", reply)

        return ChatResponse(
            reply=reply,
            intent=intent,
            session_id=key,
            products=[Product(**item) for item in products[:4]],
            credit=credit_offer,
            suggestions=self._suggestions(intent, products, credit_offer),
            source=source,
        )

    def get_history(self, key: str) -> List[Dict[str, str]]:
        return self.sessions.history(key)

    def reset(self, key: str) -> None:
        self.sessions.reset(key)

    # ------------------------------------------------------------------
    # Recuperación de datos
    # ------------------------------------------------------------------
    def _retrieve_products(
        self,
        message: str,
        entities: Dict[str, Any],
        city: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Busca productos y aplica un fallback de ciudad si no hay inventario local."""
        products = self.repository.list_products(
            city=city,
            category=entities.get("category"),
            color=entities.get("color"),
            max_price=entities.get("max_price"),
            query=None if (entities.get("category") or entities.get("color")) else message,
            limit=6,
        )
        if not products and city:
            products = self.repository.list_products(
                city=None,
                category=entities.get("category"),
                color=entities.get("color"),
                max_price=entities.get("max_price"),
                query=message,
                limit=6,
            )
        return products

    def _build_credit_offer(
        self,
        entities: Dict[str, Any],
        products: List[Dict[str, Any]],
        customer: Optional[Dict[str, Any]],
    ) -> CreditOffer:
        """Genera la simulación CrediJamar a partir del mensaje o del producto."""
        price = None
        if products:
            price = products[0]["price"]
        if not price:
            price = entities.get("max_price") or 2_000_000
        term = entities.get("term_weeks") or 24
        down = entities.get("down_payment") or 0
        profile = customer or demo_customer("invitado-jamar")
        offer = simulate_credit(price=price, down_payment=down, term_weeks=term, customer=profile)
        return CreditOffer(**offer)

    # ------------------------------------------------------------------
    # Generación de respuesta
    # ------------------------------------------------------------------
    def _llm_reply(
        self,
        message: str,
        intent: str,
        entities: Dict[str, Any],
        products: List[Dict[str, Any]],
        credit_offer: Optional[CreditOffer],
        customer: Optional[Dict[str, Any]],
        key: str,
        city: Optional[str],
    ) -> str:
        """Compone la respuesta con Google Gemini usando el contexto recuperado."""
        assert self._client is not None

        try:
            from google.genai import types
        except Exception:  # pragma: no cover - dependencia ausente
            logger.exception("SDK de Google Gemini no disponible")
            return ""

        compact_products = [
            {
                "nombre": item["name"],
                "categoria": item["category"],
                "color": item["color"],
                "precio": item["price"],
                "dimensiones": item["dimensions"],
                "stock": item["stock"],
                "ciudad": city,
                "descripcion": item["description"],
            }
            for item in products[:4]
        ]
        context: Dict[str, Any] = {
            "intencion": intent,
            "ciudad_detectada": city,
            "cliente": {
                "nombre": customer.get("name") if customer else None,
                "segmento": customer.get("segment") if customer else None,
                "ciudad": customer.get("city") if customer else None,
                "score": customer.get("credit_score") if customer else None,
                "compras_previas": customer.get("purchases") if customer else None,
            },
            "productos": compact_products,
            "credito": credit_offer.model_dump() if credit_offer else None,
            "datos_extraidos": {
                "presupuesto": entities.get("max_price"),
                "categoria": entities.get("category"),
                "color": entities.get("color"),
                "plazo_semanas": entities.get("term_weeks"),
            },
        }

        system_prompt = (
            "Eres el Asistente Jamar, asesor de interiores y ventas de Muebles Jamar en Colombia. "
            "Hablas español colombiano, con tono cálido, profesional y directo. "
            "Reglas obligatorias: no uses emojis; no inventes precios, stock ni condiciones de crédito; "
            "usa exclusivamente el contexto entregado; si no hay productos adecuados dilo con claridad; "
            "menciona precios en pesos colombianos con separador de miles; si hay una oferta CrediJamar "
            "indica estado, cuota semanal y plazo; cierra con una sola pregunta de seguimiento. "
            "Responde en máximo 150 palabras y evita listas extensas."
        )
        context_json = json.dumps(context, ensure_ascii=False, default=str)
        system_instruction = (
            f"{system_prompt}\n\nContexto recuperado en tiempo real (JSON): {context_json}"
        )

        contents: List[Any] = []
        for turn in self.sessions.history(key)[-8:]:
            role = "user" if turn["role"] == "user" else "model"
            contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=turn["content"])])
            )
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))

        try:
            response = self._client.models.generate_content(
                model=self.settings.gemini_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.4,
                    max_output_tokens=450,
                ),
            )
            return (response.text or "").strip()
        except Exception:
            logger.exception("Fallo al generar respuesta con Gemini; se usa plantilla local")
            return ""

    def _fallback_reply(
        self,
        intent: str,
        entities: Dict[str, Any],
        products: List[Dict[str, Any]],
        credit_offer: Optional[CreditOffer],
        customer: Optional[Dict[str, Any]],
        city: Optional[str],
    ) -> str:
        """Plantillas profesionales para operación sin motor generativo."""
        name = (customer or {}).get("name", "").split(" ")[0]

        if intent == "greeting":
            greeting = f"Hola, {name}. " if name else "Hola. "
            return (
                greeting
                + "Soy el Asistente Jamar y puedo ayudarte a amueblar tu hogar, consultar "
                "disponibilidad por ciudad, analizar una foto de tu espacio y simular tu "
                "crédito CrediJamar. ¿Qué espacio quieres renovar?"
            )

        if intent == "human_handoff":
            return (
                "Puedo conectar tu caso con un asesor especializado de Muebles Jamar. "
                "Cuéntame qué producto te interesa y en qué ciudad estás para transferir "
                "el contexto completo. "
                "¿Deseas que prepare el resumen de la conversación?"
            )

        if intent == "order_status":
            return (
                "Para consultar el estado de un pedido necesito el número de orden o el "
                "documento asociado a la compra. También puedo transferirte con un asesor "
                "de servicio al cliente. "
                "¿Cuál es el número de pedido?"
            )

        if intent == "vision":
            return (
                "Puedo analizar una foto de tu sala, comedor, alcoba u oficina para "
                "recomendarte muebles por color, estilo y dimensiones. Adjunta la imagen "
                "con el botón de cámara y cuéntame si tienes un presupuesto o ciudad de entrega."
            )

        if intent == "credit" and credit_offer:
            return self._credit_reply(credit_offer)

        if products:
            intro = "Encontré estas opciones que se ajustan a lo que buscas:"
            if city:
                intro = f"Estas son las opciones disponibles para {city}:"
            lines = [intro]
            for item in products[:3]:
                stock_note = (
                    f"{item['stock']} unidades en {city}"
                    if city
                    else f"{item['stock']} unidades en total"
                )
                lines.append(
                    f"- {item['name']} en {item['color'].lower()}: {format_cop(item['price'])}, "
                    f"{item['dimensions']}, {stock_note}."
                )
            lines.append(
                "Puedo simular la cuota semanal de CrediJamar o revisar otra ciudad. "
                "¿Cuál de estas opciones te interesa?"
            )
            return "\n".join(lines)

        if intent == "stock":
            return (
                "Puedo revisar disponibilidad por ciudad en Bogotá, Medellín, Cali, "
                "Barranquilla, Cartagena y Bucaramanga. Indícame el producto y la ciudad "
                "donde lo necesitas. ¿Cuál deseas consultar?"
            )

        if intent == "product_search":
            filters = []
            if entities.get("category"):
                filters.append(entities["category"].lower())
            if entities.get("color"):
                filters.append(entities["color"].lower())
            if entities.get("max_price"):
                filters.append(f"hasta {format_cop(entities['max_price'])}")
            filter_text = " " + " ".join(filters) if filters else ""
            return (
                f"No encontré productos{filter_text} con esos criterios. "
                "Puedo ampliar el presupuesto, revisar otra ciudad o mostrarte alternativas "
                "de la misma categoría. ¿Qué prefieres ajustar?"
            )

        return (
            "Puedo ayudarte con el catálogo, disponibilidad por ciudad, análisis visual de "
            "espacios y simulación de crédito CrediJamar. Cuéntame qué mueble buscas, "
            "para qué espacio y en qué ciudad estás. ¿Cómo puedo asesorarte hoy?"
        )

    def _credit_reply(self, offer: CreditOffer) -> str:
        status_text = {
            "pre_aprobado": "pre-aprobada",
            "requiere_validacion": "con revisión adicional",
            "no_aprobado": "no aprobada en esta simulación",
        }.get(offer.status, offer.status)
        return (
            f"Tu compra de {format_cop(offer.price)} quedó {status_text} con CrediJamar. "
            f"Con una cuota inicial de {format_cop(offer.down_payment)} y un plazo de "
            f"{offer.term_weeks} semanas, la cuota estimada es {format_cop(offer.weekly_payment)} "
            f"semanales ({format_cop(offer.monthly_payment)} al mes). "
            f"{offer.reason} ¿Quieres ajustar la cuota inicial o el plazo?"
        )

    def _suggestions(
        self,
        intent: str,
        products: List[Dict[str, Any]],
        credit_offer: Optional[CreditOffer],
    ) -> List[str]:
        if credit_offer:
            return ["Cambiar plazo a 36 semanas", "Aumentar la cuota inicial", "Ver productos disponibles"]
        if intent == "product_search" and products:
            return ["Ver disponibilidad en mi ciudad", "Simular crédito para esta compra", "Buscar opciones más económicas"]
        if intent == "product_search":
            return ["Ampliar el presupuesto", "Buscar en otra ciudad", "Ver catálogo completo"]
        if intent == "vision":
            return ["Analizar otra foto", "Buscar sala en Bogotá", "Simular crédito"]
        if intent == "greeting":
            return ["Buscar un sofá", "Simular crédito CrediJamar", "Analizar una foto de mi sala"]
        return ["Ver catálogo", "Consultar disponibilidad", "Hablar con un asesor"]


_agent_instance: Optional[JamarAgent] = None
_agent_lock = threading.Lock()


def get_agent() -> JamarAgent:
    """Singleton del agente con inicialización diferida."""
    global _agent_instance
    if _agent_instance is None:
        with _agent_lock:
            if _agent_instance is None:
                _agent_instance = JamarAgent(get_snowflake_client())
    return _agent_instance
