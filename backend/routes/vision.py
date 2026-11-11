"""Análisis visual de espacios con IA.

Recibe una fotografía del hogar y recomienda productos por color, estilo y
categoría. Usa la API de visión de Google Gemini cuando está disponible y, en
su defecto, aplica un análisis heurístico de paleta con Pillow para mantener la
funcionalidad en modo demostración.
"""

from __future__ import annotations

import io
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image, ImageOps, ImageStat

from agent import get_agent, strip_emojis
from config import get_settings
from schemas import VisionAnalysis, VisionResponse, Product
from snowflake_client import get_snowflake_client, normalize_text

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Visión"])

MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg", "image/heic", "image/heif"}

KNOWN_COLORS: Dict[str, str] = {
    "Blanco": "#F2F0EC",
    "Crema": "#E8DFCE",
    "Beige": "#CDBBA2",
    "Gris": "#8A8D8F",
    "Negro": "#2B2B2B",
    "Madera": "#8B5E3C",
    "Nogal": "#7A4E2D",
    "Miel": "#B07A3F",
    "Verde": "#3F6B52",
    "Azul": "#3A5A78",
    "Terracota": "#B5654A",
    "Café": "#5E4433",
}

ROOM_TO_CATEGORY: Dict[str, str] = {
    "sala": "Sala",
    "salon": "Sala",
    "comedor": "Comedor",
    "alcoba": "Alcoba",
    "habitacion": "Alcoba",
    "dormitorio": "Alcoba",
    "oficina": "Oficina",
    "estudio": "Oficina",
    "almacenamiento": "Almacenamiento",
    "closet": "Almacenamiento",
}


def _hex_to_rgb(value: str) -> Tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _distance(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> float:
    """Distancia perceptual simplificada (ponderación de canal verde)."""
    return (
        2 * (a[0] - b[0]) ** 2
        + 4 * (a[1] - b[1]) ** 2
        + 3 * (a[2] - b[2]) ** 2
    ) ** 0.5


def _nearest_color(rgb: Tuple[int, int, int]) -> Tuple[str, str]:
    name, hex_value = min(
        KNOWN_COLORS.items(),
        key=lambda item: _distance(rgb, _hex_to_rgb(item[1])),
    )
    return name, hex_value


def _dominant_colors(image: Image.Image, max_colors: int = 4) -> List[Dict[str, Any]]:
    """Extrae la paleta dominante y la asocia a nombres comerciales."""
    img = image.convert("RGB")
    img.thumbnail((200, 200))
    quantized = img.quantize(colors=10, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette() or []
    raw = quantized.getcolors(maxcolors=256) or []
    raw.sort(key=lambda item: item[0], reverse=True)
    total = sum(count for count, _ in raw) or 1

    results: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for count, index in raw:
        start = index * 3
        rgb = tuple(palette[start : start + 3])
        if len(rgb) < 3:
            continue
        name, hex_value = _nearest_color(rgb)  # type: ignore[arg-type]
        if name in seen:
            continue
        seen.add(name)
        results.append(
            {
                "name": name,
                "hex": hex_value,
                "share": round(count / total, 2),
            }
        )
        if len(results) >= max_colors:
            break
    return results


def _detect_room(room_hint: Optional[str], filename: Optional[str]) -> str:
    """Infiere el tipo de espacio a partir del formulario o del nombre del archivo."""
    for candidate in (room_hint, filename):
        normalized = normalize_text(candidate or "")
        for keyword, category in ROOM_TO_CATEGORY.items():
            if keyword in normalized:
                return category
    return "Sala"


def _style_from_colors(color_names: List[str]) -> str:
    names = set(color_names)
    if names & {"Gris", "Blanco", "Negro"}:
        return "Contemporáneo"
    if names & {"Beige", "Crema", "Madera", "Miel", "Nogal"}:
        return "Nórdico cálido"
    if names & {"Verde", "Azul"}:
        return "Natural"
    if names & {"Terracota", "Café"}:
        return "Mediterráneo cálido"
    return "Transición"


def _heuristic_analysis(image: Image.Image, room_type: str) -> Dict[str, Any]:
    """Análisis local con Pillow cuando no hay proveedor de visión disponible."""
    colors = _dominant_colors(image)
    color_names = [item["name"] for item in colors]
    brightness = ImageStat.Stat(image.convert("L")).mean[0]
    light = "iluminación natural y abundante" if brightness > 150 else "iluminación cálida y controlada"
    style = _style_from_colors(color_names)
    palette_text = ", ".join(color_names[:3])
    return {
        "room_type": room_type,
        "style": style,
        "dominant_colors": color_names,
        "notes": (
            f"Predominan tonos {palette_text.lower()} con {light}. "
            "Conviene equilibrar con muebles de líneas limpias y materiales cálidos."
        ),
        "recommended_category": room_type,
        "source": "heuristic",
        "palette_hex": [item["hex"] for item in colors],
    }


def _gemini_analysis(image: Image.Image, room_hint: str) -> Optional[Dict[str, Any]]:
    """Solicita un análisis estructurado al modelo de visión de Google Gemini."""
    settings = get_settings()
    if not settings.ai_enabled:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(
                timeout=int(settings.gemini_timeout_seconds * 1000)
            ),
        )
        prepared = ImageOps.exif_transpose(image).convert("RGB")
        prepared.thumbnail((1280, 1280))
        buffer = io.BytesIO()
        prepared.save(buffer, format="JPEG", quality=85)

        prompt = (
            "Analiza esta fotografía de un espacio interior de un hogar colombiano. "
            "Responde ÚNICAMENTE un objeto JSON válido con las claves: "
            "room_type (Sala, Comedor, Alcoba, Oficina o Almacenamiento), "
            "style (estilo decorativo en español), dominant_colors (arreglo de nombres de color en español), "
            "notes (máximo 30 palabras con recomendaciones de decoración), "
            "recommended_category (misma categoría que room_type). "
            f"Pista del usuario sobre la habitación: {room_hint}."
        )
        response = client.models.generate_content(
            model=settings.gemini_vision_model,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(
                            data=buffer.getvalue(),
                            mime_type="image/jpeg",
                        ),
                    ],
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=300,
                response_mime_type="application/json",
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        content = (response.text or "").strip()
        content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
        data = json.loads(content)

        room_type = str(data.get("room_type") or room_hint or "Sala")
        category = str(data.get("recommended_category") or room_type)
        colors = [str(item) for item in data.get("dominant_colors", []) if str(item).strip()]
        return {
            "room_type": room_type,
            "style": str(data.get("style") or "Contemporáneo"),
            "dominant_colors": colors or ["Neutro"],
            "notes": str(data.get("notes") or "El espacio admite una composición equilibrada y funcional."),
            "recommended_category": category,
            "source": "gemini_vision",
            "palette_hex": [KNOWN_COLORS.get(color, "#B9B4A8") for color in colors],
        }
    except Exception:
        logger.exception("Análisis de visión con Gemini fallido; se usa análisis heurístico")
        return None


def _prepare_image(content: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(content))
        image.load()
        return ImageOps.exif_transpose(image).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="La imagen no es válida o está dañada") from exc


def _rank_products(products: List[Dict[str, Any]], palette_hex: List[str]) -> List[Dict[str, Any]]:
    """Ordena productos por cercanía de color respecto a la paleta detectada."""
    targets = [_hex_to_rgb(hex_value) for hex_value in palette_hex if hex_value]

    def score(product: Dict[str, Any]) -> float:
        product_hex = product.get("color_hex") or "#B9B4A8"
        rgb = _hex_to_rgb(product_hex)
        color_score = min((_distance(rgb, target) for target in targets), default=0)
        return color_score - float(product.get("rating", 4.0)) * 8

    return sorted(products, key=score)


@router.post("/vision", response_model=VisionResponse, summary="Analiza una foto de un espacio")
async def analyze_space(
    file: UploadFile = File(..., description="Fotografía del espacio (JPG, PNG o WEBP)"),
    user_id: Optional[str] = Form(default=None),
    session_id: Optional[str] = Form(default=None),
    city: Optional[str] = Form(default=None),
    budget: Optional[float] = Form(default=None),
    room_type: Optional[str] = Form(default=None),
) -> VisionResponse:
    """Analiza el espacio y devuelve recomendaciones de producto compatibles."""
    if file.content_type and file.content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Formato no soportado. Usa JPG, PNG o WEBP.")

    content = await file.read()
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="La imagen supera el límite de 8 MB.")
    if not content:
        raise HTTPException(status_code=400, detail="No se recibió ninguna imagen.")

    image = _prepare_image(content)
    detected_room = _detect_room(room_type, file.filename)

    analysis = _gemini_analysis(image, detected_room)
    if analysis is None:
        analysis = _heuristic_analysis(image, detected_room)

    # Garantiza valores consistentes en la respuesta tipada.
    category = analysis.get("recommended_category") or detected_room
    if normalize_text(category) not in {normalize_text(value) for value in ROOM_TO_CATEGORY.values()}:
        category = detected_room

    repository = get_snowflake_client()
    products = repository.list_products(
        city=city,
        category=category,
        max_price=budget,
        limit=10,
    )
    if not products:
        products = repository.list_products(city=city, max_price=budget, limit=10)
    if not products:
        products = repository.list_products(category=category, limit=10)

    ranked = _rank_products(products, analysis.get("palette_hex", []))[:4]
    color_names = analysis.get("dominant_colors", [])

    if ranked:
        names = ", ".join(item["name"] for item in ranked[:3])
        reply = (
            f"Analicé tu {analysis['room_type'].lower()}. Detecté un estilo "
            f"{analysis['style'].lower()} con paleta {', '.join(color_names[:3]).lower()}. "
            f"Seleccioné estas opciones por armonía de color y proporción: {names}. "
            "¿Quieres que simule la cuota semanal de alguna?"
        )
    else:
        reply = (
            f"Analicé tu {analysis['room_type'].lower()} y detecté un estilo "
            f"{analysis['style'].lower()}. No encontré inventario que coincida exactamente "
            "con el presupuesto o la ciudad indicada. Puedo ampliar la búsqueda o revisar "
            "otra ciudad. ¿Cuál prefieres?"
        )

    reply = strip_emojis(reply)

    # Integra el análisis al historial compartido entre canales.
    agent = get_agent()
    key = agent.sessions.resolve_key(user_id, session_id)
    agent.sessions.append(key, "user", "[Imagen adjunta: análisis de espacio]")
    agent.sessions.append(key, "assistant", reply)

    suggestions = [
        "Analizar otra foto",
        f"Buscar más muebles para {analysis['room_type'].lower()}",
        "Simular crédito CrediJamar",
    ]

    return VisionResponse(
        analysis=VisionAnalysis(
            room_type=analysis["room_type"],
            style=analysis["style"],
            dominant_colors=color_names,
            notes=analysis["notes"],
            recommended_category=category,
            source=analysis.get("source", "heuristic"),
        ),
        reply=reply,
        products=[Product(**item) for item in ranked],
        suggestions=suggestions,
        session_id=key,
    )
