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
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from advisor import advisor_status, create_advisor_request
from catalog import CATEGORY_KEYWORDS, CITY_NAMES, COLOR_KEYWORDS, demo_customer
from config import get_settings
from credit_engine import simulate_credit
from schemas import AdvisorHandoff, ChatResponse, CreditOffer, Product
from snowflake_client import SnowflakeClient, get_snowflake_client, normalize_text

logger = logging.getLogger(__name__)

_INSTRUCTIONS_PATH = Path(__file__).resolve().parent / "prompts" / "agent_instructions.md"

_FALLBACK_INSTRUCTIONS = (
    "Eres el Asistente Jamar, asesor de interiores, ventas y CrediJamar de Muebles Jamar en "
    "Colombia. Hablas español colombiano, con tono cálido, profesional y directo. "
    "Personaliza con el nombre del contexto; si no lo tienes, pídelo una sola vez. "
    "Reglas obligatorias: no uses emojis ni Markdown; no inventes precios, stock, cuotas, "
    "horarios ni condiciones de crédito; usa exclusivamente el contexto entregado; si no hay "
    "productos adecuados dilo con claridad; menciona precios en pesos colombianos con separador "
    "de miles; si hay una oferta CrediJamar indica estado, cuota semanal y plazo; si el cliente "
    "pide un asesor usa el objeto asesor y confirma el código de solicitud o el horario real; "
    "cierra con una sola pregunta de seguimiento. Responde en máximo 150 palabras."
)


@lru_cache(maxsize=1)
def get_agent_instructions() -> str:
    """Carga las instrucciones del agente desde el archivo Markdown.

    Si el archivo no está disponible (por ejemplo, en un despliegue incompleto),
    se usa un prompt mínimo embebido para no dejar al agente sin reglas.
    """
    try:
        content = _INSTRUCTIONS_PATH.read_text(encoding="utf-8").strip()
        if content:
            return content
        logger.warning("El archivo de instrucciones está vacío: %s", _INSTRUCTIONS_PATH)
    except OSError:
        logger.exception("No fue posible leer las instrucciones: %s", _INSTRUCTIONS_PATH)
    return _FALLBACK_INSTRUCTIONS


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
HUMAN_KEYWORDS = ["asesor", "asesora", "asesoría", "asesoria", "humano", "persona", "vendedor", "agente real"]
ORDER_KEYWORDS = ["pedido", "rastrear", "rastreo", "envio", "envío", "entrega", "guia", "guía"]
GREETING_KEYWORDS = ["hola", "buenos dias", "buenos días", "buenas tardes", "buenas noches", "hey", "que tal", "qué tal"]
PRODUCT_KEYWORDS = [
    "buscar",
    "busco",
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
FULL_CATALOG_PHRASES = [
    "todos los productos",
    "todos los muebles",
    "catalogo completo",
    "catalogo entero",
    "todo el catalogo",
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


NAME_STOPWORDS = {
    "y",
    "e",
    "de",
    "del",
    "la",
    "el",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",
    "para",
    "por",
    "con",
    "en",
    "que",
    "quiero",
    "busco",
    "necesito",
    "cliente",
    "asesor",
    "asesora",
    "asesoria",
    "asesoría",
}

NAME_PATTERNS = [
    re.compile(
        r"\b(?:me llamo|mi nombre es|puedes llamarme|llámame|llamame)\s+"
        r"([^\W\d_]+(?:\s+[^\W\d_]+){0,3})",
        re.IGNORECASE | re.UNICODE,
    ),
    re.compile(
        r"^\s*(?:soy)\s+([^\W\d_]+(?:\s+[^\W\d_]+){0,3})",
        re.IGNORECASE | re.UNICODE,
    ),
]


def clean_name(value: str) -> Optional[str]:
    """Normaliza un nombre recibido por API o Telegram."""
    cleaned = re.sub(r"\s+", " ", (value or "").strip(" .,;:!?¡¿\t\n"))
    if not cleaned:
        return None
    return " ".join(part.capitalize() for part in cleaned.split(" "))[:120]


def extract_name(message: str) -> Optional[str]:
    """Detecta presentaciones explícitas sin confundirlas con ciudades o roles."""
    for pattern in NAME_PATTERNS:
        match = pattern.search(message or "")
        if not match:
            continue
        words: List[str] = []
        for word in re.findall(r"[^\W\d_]+", match.group(1), flags=re.UNICODE):
            if word.lower() in NAME_STOPWORDS:
                break
            words.append(word)
            if len(words) == 3:
                break
        if words:
            return clean_name(" ".join(words))
    return None


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
    if entities["mentions_vision"]:
        return "vision"
    if entities["mentions_human"]:
        return "human_handoff"
    if entities["mentions_credit"]:
        return "credit"
    if entities["mentions_stock"]:
        return "stock"
    if any(normalize_text(word) in normalized for word in ORDER_KEYWORDS):
        return "order_status"
    if any(phrase in normalized for phrase in FULL_CATALOG_PHRASES) or entities["category"] or any(
        normalize_text(word) in normalized for word in PRODUCT_KEYWORDS
    ):
        return "product_search"
    if any(_keyword_present(normalized, word) for word in GREETING_KEYWORDS) and len(normalized.split()) <= 5:
        return "greeting"
    return "general"


class SessionStore:
    """Historial de conversación en memoria con bloqueo para concurrencia."""

    def __init__(self, max_messages: int = 16) -> None:
        self._sessions: Dict[str, List[Dict[str, str]]] = {}
        self._timestamps: Dict[str, str] = {}
        self._names: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._max_messages = max_messages

    def resolve_key(self, user_id: Optional[str], session_id: Optional[str]) -> str:
        """El `user_id` manda para compartir estado entre canales."""
        if user_id and user_id.strip():
            return f"user:{user_id.strip()}"
        if session_id and session_id.strip():
            return session_id.strip()[:128]
        return f"web:{uuid.uuid4().hex[:12]}"

    def set_name(self, key: str, name: str) -> None:
        cleaned = clean_name(name)
        if not cleaned:
            return
        with self._lock:
            self._names[key] = cleaned

    def name(self, key: str) -> Optional[str]:
        with self._lock:
            return self._names.get(key)

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
        name: Optional[str] = None,
        city: Optional[str] = None,
        channel: str = "web",
    ) -> ChatResponse:
        """Procesa un mensaje y devuelve texto, productos, crédito y asesoría."""
        key = self.sessions.resolve_key(user_id, session_id)
        if name:
            self.sessions.set_name(key, name)
        detected_name = extract_name(message)
        if detected_name:
            self.sessions.set_name(key, detected_name)
        profile_name = self.sessions.name(key)

        entities = extract_entities(message)
        intent = classify_intent(message, entities)
        normalized_message = normalize_text(message)
        full_catalog_requested = any(
            phrase in normalized_message for phrase in FULL_CATALOG_PHRASES
        )
        effective_city = city or entities.get("city")

        customer = None
        if user_id or intent in {"credit", "human_handoff"}:
            customer = self.repository.get_customer(user_id or f"web-{key.split(':')[-1]}")
        if not profile_name and customer:
            profile_name = clean_name(str(customer.get("name") or ""))
            if profile_name:
                self.sessions.set_name(key, profile_name)

        products: List[Dict[str, Any]] = []
        if intent in {"product_search", "stock", "credit"}:
            product_limit = 50 if intent == "product_search" and full_catalog_requested else 3
            products = self._retrieve_products(message, entities, effective_city, limit=product_limit)

        credit_offer: Optional[CreditOffer] = None
        if entities.get("mentions_credit") or intent == "credit":
            credit_offer = self._build_credit_offer(entities, products, customer, profile_name)

        advisor_snapshot = advisor_status()
        advisor_handoff: Optional[AdvisorHandoff] = None
        if intent == "human_handoff":
            product = products[0] if products else None
            topic = "credito" if (credit_offer or entities.get("mentions_credit")) else ("producto" if product else "general")
            handoff = create_advisor_request(
                user_id=user_id,
                session_id=session_id or key,
                name=profile_name,
                city=effective_city,
                channel=channel,
                topic=topic,
                message=message,
                product_id=product.get("id") if product else None,
                product_name=product.get("name") if product else None,
                price=product.get("price") if product else entities.get("max_price"),
            )
            advisor_handoff = AdvisorHandoff(**handoff)

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
                profile_name=profile_name,
                advisor_snapshot=advisor_snapshot,
                advisor_handoff=advisor_handoff,
                channel=channel,
            )
            source = "gemini"
            if not reply:
                reply = self._fallback_reply(
                    intent,
                    entities,
                    products,
                    credit_offer,
                    customer,
                    effective_city,
                    profile_name,
                    advisor_handoff,
                    detected_name,
                )
                source = "demo"
        else:
            reply = self._fallback_reply(
                intent,
                entities,
                products,
                credit_offer,
                customer,
                effective_city,
                profile_name,
                advisor_handoff,
                detected_name,
            )
            source = "demo"

        reply = strip_emojis(reply)
        self.sessions.append(key, "user", message)
        self.sessions.append(key, "assistant", reply)

        return ChatResponse(
            reply=reply,
            intent=intent,
            session_id=key,
            user_name=profile_name,
            products=[Product(**item) for item in (
                products if intent == "product_search" and full_catalog_requested else products[:3]
            )]
            if intent in {"product_search", "stock"}
            else [],
            credit=credit_offer,
            advisor=advisor_handoff,
            suggestions=self._suggestions(intent, products, credit_offer),
            source=source,
            data_source=self.repository.mode,
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
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """Busca productos y aplica fallbacks para no dejar el catálogo vacío."""
        products = self.repository.list_products(
            city=city,
            category=entities.get("category"),
            color=entities.get("color"),
            max_price=entities.get("max_price"),
            query=None if (entities.get("category") or entities.get("color")) else message,
            limit=limit,
        )
        if not products:
            products = self.repository.list_products(
                city=city,
                category=entities.get("category"),
                color=entities.get("color"),
                max_price=entities.get("max_price"),
                query=None,
                limit=limit,
            )
        if not products and city:
            products = self.repository.list_products(
                city=None,
                category=entities.get("category"),
                color=entities.get("color"),
                max_price=entities.get("max_price"),
                query=None,
                limit=limit,
            )
        return products

    def _build_credit_offer(
        self,
        entities: Dict[str, Any],
        products: List[Dict[str, Any]],
        customer: Optional[Dict[str, Any]],
        profile_name: Optional[str] = None,
    ) -> CreditOffer:
        """Genera la simulación CrediJamar a partir del mensaje o del producto."""
        price = None
        if products:
            price = products[0]["price"]
        if not price:
            price = entities.get("max_price") or 2_000_000
        term = entities.get("term_weeks") or 24
        down = entities.get("down_payment") or 0
        profile = dict(customer) if customer else demo_customer("invitado-jamar")
        if profile_name:
            profile["name"] = profile_name
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
        profile_name: Optional[str] = None,
        advisor_snapshot: Optional[Dict[str, Any]] = None,
        advisor_handoff: Optional[AdvisorHandoff] = None,
        channel: str = "web",
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
            for item in products[:12]
        ]
        advisor_snapshot = advisor_snapshot or {}
        context: Dict[str, Any] = {
            "intencion": intent,
            "ciudad_detectada": city,
            "usuario": {
                "nombre": profile_name,
                "canal": channel,
            },
            "cliente": {
                "nombre": profile_name or (customer.get("name") if customer else None),
                "segmento": customer.get("segment") if customer else None,
                "ciudad": customer.get("city") if customer else None,
                "score": customer.get("credit_score") if customer else None,
                "compras_previas": customer.get("purchases") if customer else None,
            },
            "productos": compact_products,
            "credito": credit_offer.model_dump() if credit_offer else None,
            "asesor": {
                "disponible": advisor_snapshot.get("open"),
                "horario": advisor_snapshot.get("schedule"),
                "zona_horaria": advisor_snapshot.get("timezone"),
                "hora_local": advisor_snapshot.get("local_time"),
                "fecha_local": advisor_snapshot.get("local_date"),
                "cierre": advisor_snapshot.get("closing_at_label"),
                "siguiente_apertura": advisor_snapshot.get("next_opening_label"),
                "mensaje": advisor_snapshot.get("message"),
                "solicitud": advisor_handoff.model_dump() if advisor_handoff else None,
            },
            "datos_extraidos": {
                "presupuesto": entities.get("max_price"),
                "categoria": entities.get("category"),
                "color": entities.get("color"),
                "plazo_semanas": entities.get("term_weeks"),
            },
        }

        system_prompt = get_agent_instructions()
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

        candidates: List[str] = []
        for name in (
            self.settings.gemini_model,
            "gemini-2.5-flash-lite",
            "gemini-3.8-flash",
            "gemini-flash-latest",
        ):
            if name and name not in candidates:
                candidates.append(name)

        for model_name in candidates:
            try:
                response = self._client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.4,
                        max_output_tokens=450,
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                    ),
                )
                text = (response.text or "").strip()
                if text:
                    if model_name != self.settings.gemini_model:
                        logger.info("Gemini respondió con el modelo alterno %s", model_name)
                    return text
                logger.warning("Gemini devolvió una respuesta vacía con %s", model_name)
            except Exception as exc:
                logger.warning("Fallo al generar respuesta con Gemini (%s): %s", model_name, exc)
        logger.error("No fue posible generar respuesta con Gemini; se usa plantilla local")
        return ""

    def _fallback_reply(
        self,
        intent: str,
        entities: Dict[str, Any],
        products: List[Dict[str, Any]],
        credit_offer: Optional[CreditOffer],
        customer: Optional[Dict[str, Any]],
        city: Optional[str],
        profile_name: Optional[str] = None,
        advisor_handoff: Optional[AdvisorHandoff] = None,
        detected_name: Optional[str] = None,
    ) -> str:
        """Plantillas profesionales para operación sin motor generativo."""
        name = (profile_name or detected_name or (customer or {}).get("name", "")).split(" ")[0]

        if detected_name and intent in {"general", "greeting"}:
            return (
                f"Un gusto, {clean_name(detected_name)}. Soy el Asistente Jamar y puedo "
                "ayudarte con catálogo, disponibilidad, análisis de fotos, CrediJamar y "
                "asesoría personalizada. ¿Qué espacio quieres renovar o qué producto buscas?"
            )

        if intent == "greeting":
            if name:
                return (
                    f"Hola, {name}. Soy el Asistente Jamar y puedo ayudarte a amueblar tu "
                    "hogar, consultar disponibilidad por ciudad, analizar una foto de tu "
                    "espacio y simular tu crédito CrediJamar. ¿Qué espacio quieres renovar?"
                )
            return (
                "Hola. Soy el Asistente Jamar y puedo ayudarte a amueblar tu hogar, "
                "consultar disponibilidad por ciudad, analizar una foto de tu espacio y "
                "simular tu crédito CrediJamar. Para personalizar la asesoría, ¿cómo te "
                "llamas y qué espacio quieres renovar?"
            )

        if intent == "human_handoff":
            if advisor_handoff:
                prefix = f"Listo, {name}. " if name else "Listo. "
                if advisor_handoff.available:
                    return (
                        f"{prefix}Registré tu solicitud {advisor_handoff.request_id} para "
                        "asesoría personalizada. Un asesor de Muebles Jamar continuará la "
                        f"conversación en el horario de atención actual. Horario: {advisor_handoff.schedule}. "
                        "¿Quieres dejar algún detalle adicional sobre el producto o la ciudad?"
                    )
                next_text = (
                    f" La próxima apertura es {advisor_handoff.next_opening_label}"
                    if advisor_handoff.next_opening_label
                    else ""
                )
                return (
                    f"{prefix}Registré tu solicitud {advisor_handoff.request_id} para "
                    "asesoría personalizada. En este momento el horario está cerrado."
                    f"{next_text} Horario de atención: {advisor_handoff.schedule}. "
                    "Un asesor revisará el contexto de esta conversación. "
                    "¿Quieres que revise mientras tanto productos o una simulación CrediJamar?"
                )
            return (
                "Puedo conectar tu caso con un asesor especializado de Muebles Jamar. "
                "Cuéntame qué producto te interesa y en qué ciudad estás para transferir "
                "el contexto completo. ¿Deseas que prepare el resumen de la conversación?"
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
            for item in products[:10]:
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
        if intent == "human_handoff":
            return ["Ver catálogo", "Simular crédito CrediJamar", "Consultar disponibilidad"]
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
