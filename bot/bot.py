"""Bot de Telegram del Asistente Jamar.

Integra comandos interactivos, catálogo, simulación CrediJamar, análisis de
fotos y la Mini App web. La identidad `tg-<id>` se comparte con la Mini App,
por lo que el historial de conversación se mantiene entre ambos canales.

Requiere `TELEGRAM_BOT_TOKEN`, `API_BASE_URL` (backend) y `PUBLIC_WEBAPP_URL`
(frontend accesible desde Telegram).
"""

from __future__ import annotations

import html
import logging
import os
import time
from urllib.parse import quote

import httpx
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
PUBLIC_WEBAPP_URL = os.getenv("PUBLIC_WEBAPP_URL", "http://localhost:3000").rstrip("/")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

CATEGORIES = ["Sala", "Comedor", "Alcoba", "Almacenamiento", "Oficina"]

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("jamar.bot")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def esc(value: object) -> str:
    """Escapa texto para los mensajes HTML de Telegram."""
    return html.escape(str(value or ""))


def cop(value: object) -> str:
    """Formato de pesos colombianos."""
    try:
        return "$ " + f"{int(round(float(value))):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$ 0"


def short(value: str, size: int = 28) -> str:
    value = str(value)
    return value if len(value) <= size else value[: size - 1].rstrip() + "…"


def user_key(update: Update) -> str:
    user = update.effective_user
    return f"tg-{user.id}" if user else "tg-anonimo"


def webapp_url(extra: str = "") -> str:
    base = f"{PUBLIC_WEBAPP_URL}/?open=1"
    return f"{base}{extra}" if extra else base


WEBAPP_ENABLED = PUBLIC_WEBAPP_URL.startswith("https://")


def webapp_button(label: str, url: str | None = None) -> InlineKeyboardButton | None:
    """Devuelve un botón WebApp solo si la URL pública cumple el requisito HTTPS."""
    if not WEBAPP_ENABLED:
        return None
    return InlineKeyboardButton(label, web_app=WebAppInfo(url=url or webapp_url()))


def main_menu() -> InlineKeyboardMarkup:
    """Menú principal de la experiencia Telegram."""
    rows = [
        [
            InlineKeyboardButton("Catálogo", callback_data="menu:catalog"),
            InlineKeyboardButton("CrediJamar", callback_data="menu:credit"),
        ],
    ]
    mini = webapp_button("Abrir Mini App")
    if mini:
        rows.append([mini])
    rows.append(
        [
            InlineKeyboardButton("Hablar con un asesor", callback_data="menu:advisor"),
            InlineKeyboardButton("Ayuda", callback_data="menu:help"),
        ]
    )
    return InlineKeyboardMarkup(rows)


def category_menu() -> InlineKeyboardMarkup:
    rows = []
    row: list[InlineKeyboardButton] = []
    for category in CATEGORIES:
        row.append(InlineKeyboardButton(category, callback_data=f"cat:{category}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("Volver al menú", callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)


def product_keyboard(products: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                f"Ver {short(product.get('name', 'producto'), 30)}",
                callback_data=f"prod:{product.get('id')}",
            )
        ]
        for product in products
    ]
    mini = webapp_button("Abrir Mini App")
    if mini:
        rows.append([mini])
    return InlineKeyboardMarkup(rows)


def product_text(product: dict, index: int | None = None) -> str:
    prefix = f"{index}. " if index else ""
    stock = int(product.get("stock") or 0)
    availability = (
        f"{stock} unidades disponibles" if stock > 0 else "Disponibilidad bajo pedido"
    )
    return (
        f"{prefix}<b>{esc(product.get('name'))}</b>\n"
        f"{cop(product.get('price'))} · {esc(product.get('color'))}\n"
        f"{esc(product.get('dimensions'))} · {esc(product.get('material'))}\n"
        f"{esc(availability)}"
    )


def products_message(products: list[dict], heading: str, city: str | None = None) -> str:
    location = f" en {esc(city)}" if city else ""
    blocks = [f"<b>{esc(heading)}{location}</b>"]
    for index, product in enumerate(products, start=1):
        blocks.append(product_text(product, index))
    blocks.append("Selecciona un producto para ver su ficha completa.")
    return "\n\n".join(blocks)


PRODUCTS_PER_MESSAGE = 8


async def send_product_chunks(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    products: list[dict],
    heading: str,
    city: str | None = None,
) -> None:
    """Envía todos los productos en bloques para respetar el límite de Telegram."""
    for start in range(0, len(products), PRODUCTS_PER_MESSAGE):
        chunk = products[start : start + PRODUCTS_PER_MESSAGE]
        await context.bot.send_message(
            chat_id=chat_id,
            text=products_message(chunk, heading, city),
            reply_markup=product_keyboard(chunk),
            parse_mode="HTML",
        )


# ---------------------------------------------------------------------------
# Cliente HTTP interno
# ---------------------------------------------------------------------------
async def api_request(
    context: ContextTypes.DEFAULT_TYPE,
    method: str,
    path: str,
    **kwargs,
) -> dict | list | None:
    client: httpx.AsyncClient = context.application.bot_data["http"]
    try:
        response = await client.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as error:
        detail = ""
        try:
            detail = error.response.json().get("detail", "")
        except Exception:
            detail = error.response.text[:200]
        logger.warning("API %s %s devolvió %s: %s", method, path, error.response.status_code, detail)
        return None
    except Exception:
        logger.exception("Error de comunicación con la API en %s %s", method, path)
        return None


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    name = user.first_name if user else ""
    greeting = f"Hola, {esc(name)}." if name else "Hola."
    text = (
        f"<b>{greeting} Soy el Asistente Jamar.</b>\n\n"
        "Puedo ayudarte a amueblar tu hogar, consultar inventario por ciudad, "
        "simular tu crédito CrediJamar y analizar fotos de tus espacios.\n\n"
        "Escríbeme lo que buscas o adjunta una fotografía. También puedes abrir "
        "la Mini App para una experiencia completa con carrito y simulador."
    )
    await update.message.reply_text(text, reply_markup=main_menu(), parse_mode="HTML")


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "<b>Menú del Asistente Jamar</b>\nSelecciona una opción para continuar.",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )


async def cmd_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "<b>Catálogo Jamar</b>\nElige una categoría para revisar disponibilidad.",
        reply_markup=category_menu(),
        parse_mode="HTML",
    )


async def cmd_credit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = user_key(update)
    await show_credit_preapproval(context, update.effective_chat.id, uid)


async def cmd_advisor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_advisor_status(context, update.effective_chat.id)


async def cmd_mini(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not WEBAPP_ENABLED:
        await update.message.reply_text(
            "<b>Mini App no disponible</b>\n"
            "Telegram solo permite abrir Mini Apps desde una URL pública HTTPS. "
            "Mientras configuras un dominio o túnel, puedes usar /productos, "
            "/credito o escribirme directamente por aquí.",
            reply_markup=main_menu(),
            parse_mode="HTML",
        )
        return

    await update.message.reply_text(
        "<b>Mini App del Asistente Jamar</b>\n"
        "Abre la experiencia completa sin salir de Telegram. Tu conversación se "
        "mantiene sincronizada con este chat.",
        reply_markup=InlineKeyboardMarkup(
            [
                [webapp_button("Abrir Mini App", webapp_url())],
                [webapp_button("Simulador CrediJamar", webapp_url("&credit=1"))],
            ]
        ),
        parse_mode="HTML",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "<b>Ayuda del Asistente Jamar</b>\n\n"
        "/start · Iniciar la conversación\n"
        "/menu · Menú principal\n"
        "/productos · Explorar catálogo por categoría\n"
        "/credito · Consultar cupo CrediJamar\n"
        "/asesor · Horario y solicitud de asesoría\n"
        "/mini · Abrir la Mini App\n"
        "/reset · Iniciar una conversación nueva\n\n"
        "También puedes escribir en lenguaje natural o enviar una foto de tu sala, "
        "comedor, alcoba u oficina para recibir recomendaciones."
    )
    await update.message.reply_text(text, reply_markup=main_menu(), parse_mode="HTML")


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = user_key(update)
    await api_request(
        context,
        "DELETE",
        f"/api/chat/history/{uid}",
        params={"user_id": uid},
    )
    await update.message.reply_text(
        "Conversación reiniciada. ¿Qué espacio quieres renovar?",
        reply_markup=main_menu(),
    )


async def show_credit_preapproval(context: ContextTypes.DEFAULT_TYPE, chat_id: int, uid: str) -> None:
    data = await api_request(context, "GET", f"/api/credit/preapproval/{uid}")
    if not data:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "No pude consultar tu cupo en este momento. Puedes intentarlo de nuevo "
                "en unos segundos o abrir la Mini App."
            ),
            reply_markup=main_menu(),
        )
        return

    text = (
        f"<b>CrediJamar</b>\n"
        f"Titular: {esc(data.get('customer_name'))}\n"
        f"Score: {esc(data.get('credit_score'))}\n"
        f"Cupo pre-aprobado: <b>{cop(data.get('max_amount'))}</b>\n\n"
        "La cuota final depende del producto, la cuota inicial y el plazo. "
        "Puedes simular todos los escenarios en la Mini App."
    )
    rows = []
    mini = webapp_button("Simular en la Mini App", webapp_url("&credit=1"))
    if mini:
        rows.append([mini])
    rows.append([InlineKeyboardButton("Ver catálogo", callback_data="menu:catalog")])
    rows.append([InlineKeyboardButton("Hablar con un asesor", callback_data="menu:advisor")])
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(rows),
        parse_mode="HTML",
    )


async def show_advisor_status(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Muestra el horario real y permite registrar la solicitud de asesoría."""
    status = await api_request(context, "GET", "/api/advisor/status")
    if not status:
        await context.bot.send_message(
            chat_id=chat_id,
            text="No pude consultar el horario de asesoría en este momento. Intenta de nuevo.",
            reply_markup=main_menu(),
        )
        return

    if status.get("open"):
        state = "abierto"
        detail = f"Atendemos hasta {esc(status.get('closing_at_label'))}"
    else:
        state = "cerrado"
        detail = (
            f"Próxima apertura: {esc(status.get('next_opening_label'))}"
            if status.get("next_opening_label")
            else "La atención se reanudará en el próximo horario."
        )

    text = (
        "<b>Asesoría personalizada</b>\n"
        f"Estado: <b>Horario {state}</b>\n"
        f"Horario: {esc(status.get('schedule'))}\n"
        f"{detail}\n\n"
        "Registra tu solicitud y un asesor recibirá el contexto de esta conversación."
    )
    rows = [
        [InlineKeyboardButton("Registrar solicitud", callback_data="advisor:request")],
        [InlineKeyboardButton("Volver al menú", callback_data="menu:home")],
    ]
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(rows),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# Callbacks de botones
# ---------------------------------------------------------------------------
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    data = query.data or ""
    uid = user_key(update)
    chat = query.message.chat if query.message else update.effective_chat

    if data == "menu:home":
        await query.edit_message_text(
            "<b>Menú del Asistente Jamar</b>\nSelecciona una opción para continuar.",
            reply_markup=main_menu(),
            parse_mode="HTML",
        )
        return

    if data == "menu:catalog":
        await query.edit_message_text(
            "<b>Catálogo Jamar</b>\nElige una categoría para revisar disponibilidad.",
            reply_markup=category_menu(),
            parse_mode="HTML",
        )
        return

    if data == "menu:credit":
        rows = [
            [InlineKeyboardButton("Consultar mi cupo", callback_data="credit:preapproval")],
        ]
        mini = webapp_button("Abrir simulador", webapp_url("&credit=1"))
        if mini:
            rows.append([mini])
        rows.append([InlineKeyboardButton("Volver al menú", callback_data="menu:home")])
        await query.edit_message_text(
            "<b>CrediJamar</b>\nConsulta tu cupo pre-aprobado o abre el simulador completo.",
            reply_markup=InlineKeyboardMarkup(rows),
            parse_mode="HTML",
        )
        return

    if data == "credit:preapproval":
        await show_credit_preapproval(context, chat.id, uid)
        return

    if data == "menu:advisor":
        await query.edit_message_text(
            "<b>Asesoría personalizada</b>\nConsultando disponibilidad...",
            parse_mode="HTML",
        )
        await show_advisor_status(context, chat.id)
        return

    if data == "advisor:request":
        user = update.effective_user
        handoff = await api_request(
            context,
            "POST",
            "/api/advisor/request",
            json={
                "user_id": uid,
                "session_id": uid,
                "name": user.first_name if user else None,
                "channel": "telegram",
                "topic": "general",
                "message": "Solicitud desde el menú de asesoría de Telegram.",
            },
        )
        if not handoff:
            await query.edit_message_text(
                "No pude registrar la solicitud en este momento. Intenta de nuevo.",
                reply_markup=main_menu(),
            )
            return

        if handoff.get("available"):
            detail = (
                "Un asesor continuará la conversación en el horario de atención actual."
            )
        else:
            detail = (
                f"La próxima apertura es {esc(handoff.get('next_opening_label'))}"
                if handoff.get("next_opening_label")
                else "La solicitud se revisará cuando se reanude la atención."
            )
        text = (
            "<b>Solicitud de asesoría registrada</b>\n"
            f"Código: <b>{esc(handoff.get('request_id'))}</b>\n"
            f"Horario: {esc(handoff.get('schedule'))}\n"
            f"{detail}"
        )
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Ver catálogo", callback_data="menu:catalog")],
                    [InlineKeyboardButton("Volver al menú", callback_data="menu:home")],
                ]
            ),
            parse_mode="HTML",
        )
        return

    if data == "menu:help":
        await query.edit_message_text(
            "<b>Comandos disponibles</b>\n"
            "/menu · Menú principal\n/productos · Catálogo por categoría\n"
            "/credito · Cupo CrediJamar\n/mini · Mini App\n/reset · Nueva conversación\n\n"
            "También puedes escribir o enviar una foto de tu espacio.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Volver al menú", callback_data="menu:home")]]
            ),
            parse_mode="HTML",
        )
        return

    if data.startswith("cat:"):
        category = data.split(":", 1)[1]
        await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.TYPING)
        products = await api_request(
            context,
            "GET",
            "/api/products",
            params={"category": category, "limit": 50},
        )
        if not products:
            await chat.send_message(
                f"No encontré inventario disponible en {esc(category)} en este momento.",
                reply_markup=main_menu(),
                parse_mode="HTML",
            )
            return
        await send_product_chunks(
            context,
            chat.id,
            products,
            f"Opciones en {category}",
        )
        return

    if data.startswith("prod:"):
        product_id = data.split(":", 1)[1]
        await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.TYPING)
        product = await api_request(context, "GET", f"/api/products/{product_id}")
        if not product:
            await chat.send_message(
                "No pude recuperar la ficha del producto. Intenta con otro del catálogo.",
                reply_markup=main_menu(),
            )
            return

        stock_by_city = product.get("stock_by_city") or {}
        available = [
            f"{city}: {units}"
            for city, units in stock_by_city.items()
            if int(units) > 0
        ][:4]
        stock_text = ", ".join(available) if available else "Consultar con un asesor"
        text = (
            f"{product_text(product)}\n\n"
            f"<b>Descripción</b>\n{esc(product.get('description'))}\n\n"
            f"<b>Disponibilidad</b>\n{esc(stock_text)}"
        )
        rows = [
            [InlineKeyboardButton("Solicitar crédito", callback_data=f"credit:{product_id}")],
        ]
        mini = webapp_button("Abrir Mini App")
        if mini:
            rows.append([mini])
        rows.append([InlineKeyboardButton("Volver al catálogo", callback_data="menu:catalog")])
        await chat.send_message(
            text,
            reply_markup=InlineKeyboardMarkup(rows),
            parse_mode="HTML",
        )
        return

    if data.startswith("credit:"):
        product_id = data.split(":", 1)[1]
        await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.TYPING)
        product = await api_request(context, "GET", f"/api/products/{product_id}")
        if not product:
            await chat.send_message("No pude recuperar el producto para la simulación.")
            return

        price = float(product.get("price") or 0)
        offer = await api_request(
            context,
            "POST",
            "/api/credit-check",
            json={
                "price": price,
                "down_payment": round(price * 0.10),
                "term_weeks": 24,
                "user_id": uid,
                "product_id": product_id,
            },
        )
        if not offer:
            await chat.send_message(
                "No pude calcular la simulación en este momento. Intenta de nuevo "
                "desde la Mini App.",
                reply_markup=main_menu(),
            )
            return

        recommended_down = round(price * 0.10)
        product_name = quote(str(product.get("name") or ""), safe="")
        credit_url = webapp_url(
            f"&credit=1&price={int(price)}&product={quote(product_id, safe='')}&name={product_name}"
        )
        text = (
            f"<b>Simulación CrediJamar</b>\n"
            f"Producto: {esc(product.get('name'))}\n"
            f"Precio: {cop(price)}\n"
            f"Cuota inicial sugerida: {cop(recommended_down)}\n"
            f"Plazo: 24 semanas\n\n"
            f"Cuota semanal estimada: <b>{cop(offer.get('weekly_payment'))}</b>\n"
            f"Cuota mensual estimada: {cop(offer.get('monthly_payment'))}\n"
            f"Total a pagar: {cop(offer.get('total_to_pay'))}\n\n"
            f"Estado: <b>{esc(offer.get('status'))}</b>\n"
            f"{esc(offer.get('reason'))}"
        )
        rows = []
        mini = webapp_button("Ajustar en la Mini App", credit_url)
        if mini:
            rows.append([mini])
        rows.append([InlineKeyboardButton("Ver más productos", callback_data="menu:catalog")])
        await chat.send_message(
            text,
            reply_markup=InlineKeyboardMarkup(rows),
            parse_mode="HTML",
        )
        return

    await query.edit_message_text(
        "No reconocí esa opción. Usa /menu para volver a empezar.",
        reply_markup=main_menu(),
    )


# ---------------------------------------------------------------------------
# Mensajes de texto y fotos
# ---------------------------------------------------------------------------
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or not update.message.text:
        return
    uid = user_key(update)
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )

    data = await api_request(
        context,
        "POST",
        "/api/chat",
        json={
            "message": update.message.text[:2000],
            "user_id": uid,
            "session_id": uid,
            "name": update.effective_user.first_name if update.effective_user else None,
            "channel": "telegram",
        },
    )

    if not data:
        await update.message.reply_text(
            "No pude procesar tu mensaje en este momento. Intenta nuevamente en unos "
            "segundos o abre la Mini App.",
            reply_markup=main_menu(),
        )
        return

    reply = esc(data.get("reply"))
    credit = data.get("credit")
    if credit:
        reply += (
            f"\n\n<b>CrediJamar</b>\n"
            f"Estado: {esc(credit.get('status'))}\n"
            f"Cuota semanal: <b>{cop(credit.get('weekly_payment'))}</b>\n"
            f"Plazo: {esc(credit.get('term_weeks'))} semanas"
        )

    advisor = data.get("advisor")
    if advisor:
        next_text = (
            f"\nPróxima apertura: {esc(advisor.get('next_opening_label'))}"
            if advisor.get("next_opening_label")
            else ""
        )
        reply += (
            f"\n\n<b>Asesoría</b>\n"
            f"Solicitud: <b>{esc(advisor.get('request_id'))}</b>\n"
            f"Horario: {esc(advisor.get('schedule'))}{next_text}"
        )

    products = data.get("products") or []
    await update.message.reply_text(reply, parse_mode="HTML", reply_markup=main_menu())

    if products:
        await send_product_chunks(
            context,
            update.effective_chat.id,
            products,
            "Opciones recomendadas",
        )


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or not update.message.photo:
        return
    uid = user_key(update)
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO
    )

    try:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        content = bytes(await file.download_as_bytearray())
    except Exception:
        logger.exception("No fue posible descargar la foto de Telegram")
        await update.message.reply_text(
            "No pude descargar la imagen. Intenta enviarla nuevamente."
        )
        return

    data = await api_request(
        context,
        "POST",
        "/api/vision",
        files={"file": ("espacio.jpg", content, "image/jpeg")},
        data={"user_id": uid, "session_id": uid},
    )

    if not data:
        await update.message.reply_text(
            "No pude analizar la imagen en este momento. Intenta con otra foto o "
            "abre la Mini App.",
            reply_markup=main_menu(),
        )
        return

    analysis = data.get("analysis") or {}
    colors = ", ".join(analysis.get("dominant_colors") or [])
    text = (
        f"<b>Análisis del espacio</b>\n"
        f"Tipo: {esc(analysis.get('room_type'))}\n"
        f"Estilo: {esc(analysis.get('style'))}\n"
        f"Paleta: {esc(colors)}\n\n"
        f"{esc(data.get('reply'))}"
    )
    products = data.get("products") or []
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=main_menu(),
    )

    if products:
        await send_product_chunks(
            context,
            update.effective_chat.id,
            products,
            "Muebles compatibles",
        )


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Error no controlado en el bot", exc_info=context.error)
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Ocurrió un error inesperado. Usa /menu para continuar.",
            )
        except Exception:
            logger.exception("No fue posible notificar el error al usuario")


# ---------------------------------------------------------------------------
# Arranque
# ---------------------------------------------------------------------------
async def post_init(application: Application) -> None:
    application.bot_data["http"] = httpx.AsyncClient(
        base_url=API_BASE_URL,
        timeout=httpx.Timeout(60.0, connect=10.0),
    )
    try:
        await application.bot.set_my_commands(
            [
                ("start", "Iniciar el Asistente Jamar"),
                ("menu", "Menú principal"),
                ("productos", "Explorar catálogo"),
                ("credito", "Consultar CrediJamar"),
                ("asesor", "Horario y solicitud de asesoría"),
                ("mini", "Abrir la Mini App"),
                ("reset", "Nueva conversación"),
                ("ayuda", "Ver ayuda"),
            ]
        )
    except Exception:
        logger.exception("No fue posible registrar los comandos del bot")


async def post_shutdown(application: Application) -> None:
    client: httpx.AsyncClient | None = application.bot_data.get("http")
    if client is not None:
        await client.aclose()
    logger.info("Bot detenido y recursos liberados")


def main() -> None:
    if not TOKEN:
        logger.warning(
            "TELEGRAM_BOT_TOKEN no está configurado. El contenedor permanecerá activo "
            "sin conexión; configura el token en .env y reinicia el servicio para habilitar el bot."
        )
        while True:
            time.sleep(3600)

    logger.info("Iniciando bot | API=%s | MiniApp=%s", API_BASE_URL, PUBLIC_WEBAPP_URL)

    application = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("menu", cmd_menu))
    application.add_handler(CommandHandler("productos", cmd_products))
    application.add_handler(CommandHandler("credito", cmd_credit))
    application.add_handler(CommandHandler("asesor", cmd_advisor))
    application.add_handler(CommandHandler("mini", cmd_mini))
    application.add_handler(CommandHandler("ayuda", cmd_help))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("reset", cmd_reset))
    application.add_handler(CallbackQueryHandler(on_callback))
    application.add_handler(MessageHandler(filters.PHOTO, on_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    application.add_error_handler(on_error)

    logger.info("Bot en modo polling")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=False)


if __name__ == "__main__":
    main()
