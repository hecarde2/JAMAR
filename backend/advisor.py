"""Horario de asesoría y registro de solicitudes de handoff.

El módulo calcula la disponibilidad del equipo de asesores en la zona horaria
configurada y conserva en memoria las solicitudes recientes para evitar
duplicados cuando el cliente pulsa varias veces el botón de asesoría.
"""

from __future__ import annotations

import threading
import uuid
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from config import get_settings

_WEEKDAYS = [
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
]
_MONTHS = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def _timezone() -> tzinfo:
    settings = get_settings()
    try:
        return ZoneInfo(settings.advisor_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return timezone(timedelta(hours=-5))


def _parse_time(value: str, default: time) -> time:
    try:
        hour, minute = value.strip().split(":", 1)
        return time(hour=int(hour), minute=int(minute))
    except (AttributeError, TypeError, ValueError):
        return default


def _format_time(value: time) -> str:
    hour = value.hour % 12 or 12
    suffix = "a. m." if value.hour < 12 else "p. m."
    return f"{hour}:{value.minute:02d} {suffix}"


def _format_date(value: date) -> str:
    return f"{_WEEKDAYS[value.weekday()]} {value.day} de {_MONTHS[value.month - 1]}"


def _relative_date(value: date, today: date) -> str:
    if value == today:
        return "hoy"
    if value == today + timedelta(days=1):
        return "mañana"
    return f"el {_format_date(value)}"


def _format_moment(value: datetime) -> str:
    local = value.astimezone(_timezone())
    return f"{_relative_date(local.date(), datetime.now(_timezone()).date())} a las {_format_time(local.time())}"


def schedule_windows() -> Dict[int, tuple[time, time]]:
    """Devuelve las ventanas de atención por día de la semana (0 = lunes)."""
    settings = get_settings()
    windows = {
        0: (
            _parse_time(settings.advisor_weekday_start, time(8, 0)),
            _parse_time(settings.advisor_weekday_end, time(18, 0)),
        ),
        1: (
            _parse_time(settings.advisor_weekday_start, time(8, 0)),
            _parse_time(settings.advisor_weekday_end, time(18, 0)),
        ),
        2: (
            _parse_time(settings.advisor_weekday_start, time(8, 0)),
            _parse_time(settings.advisor_weekday_end, time(18, 0)),
        ),
        3: (
            _parse_time(settings.advisor_weekday_start, time(8, 0)),
            _parse_time(settings.advisor_weekday_end, time(18, 0)),
        ),
        4: (
            _parse_time(settings.advisor_weekday_start, time(8, 0)),
            _parse_time(settings.advisor_weekday_end, time(18, 0)),
        ),
        5: (
            _parse_time(settings.advisor_saturday_start, time(9, 0)),
            _parse_time(settings.advisor_saturday_end, time(13, 0)),
        ),
    }
    if settings.advisor_sunday_enabled:
        windows[6] = (
            _parse_time(settings.advisor_sunday_start, time(9, 0)),
            _parse_time(settings.advisor_sunday_end, time(13, 0)),
        )
    return {day: window for day, window in windows.items() if window[0] < window[1]}


def schedule_label() -> str:
    """Etiqueta legible del horario configurado."""
    settings = get_settings()
    windows = schedule_windows()
    parts = []
    weekday = windows.get(0)
    saturday = windows.get(5)
    sunday = windows.get(6)
    if weekday:
        parts.append(
            f"Lunes a viernes de {_format_time(weekday[0])} a {_format_time(weekday[1])}"
        )
    if saturday:
        parts.append(
            f"sábados de {_format_time(saturday[0])} a {_format_time(saturday[1])}"
        )
    if sunday:
        parts.append(
            f"domingos de {_format_time(sunday[0])} a {_format_time(sunday[1])}"
        )
    if not parts:
        return "Horario de asesoría no configurado"
    return "; ".join(parts) + f" ({settings.advisor_timezone})"


def advisor_status(now: Optional[datetime] = None) -> Dict[str, Any]:
    """Calcula si la asesoría está abierta y cuándo vuelve a abrir."""
    tz = _timezone()
    local = (now or datetime.now(timezone.utc)).astimezone(tz)
    windows = schedule_windows()
    today_window = windows.get(local.weekday())

    open_now = False
    closing_at: Optional[datetime] = None
    if today_window:
        start, end = today_window
        if start <= local.time() < end:
            open_now = True
            closing_at = datetime.combine(local.date(), end, tzinfo=tz)

    next_opening: Optional[datetime] = None
    if not open_now:
        for offset in range(0, 8):
            day = local.date() + timedelta(days=offset)
            window = windows.get(day.weekday())
            if not window:
                continue
            candidate = datetime.combine(day, window[0], tzinfo=tz)
            if candidate > local:
                next_opening = candidate
                break

    if open_now and closing_at:
        message = (
            "El horario de asesoría está abierto. "
            f"Atendemos hasta las {_format_time(closing_at.time())}"
        )
    elif next_opening:
        message = (
            "El horario de asesoría está cerrado. "
            f"La próxima apertura es {_format_moment(next_opening)}"
        )
    else:
        message = "El horario de asesoría está cerrado temporalmente."

    return {
        "open": open_now,
        "timezone": get_settings().advisor_timezone,
        "schedule": schedule_label(),
        "local_time": local.strftime("%H:%M"),
        "local_date": _format_date(local.date()),
        "closing_at": closing_at.isoformat() if closing_at else None,
        "closing_at_label": _format_moment(closing_at) if closing_at else None,
        "next_opening": next_opening.isoformat() if next_opening else None,
        "next_opening_label": _format_moment(next_opening) if next_opening else None,
        "message": message,
    }


class AdvisorRequestStore:
    """Registro en memoria de solicitudes de asesoría con deduplicación."""

    def __init__(self, dedupe_minutes: int = 30) -> None:
        self._requests: Dict[str, Dict[str, Any]] = {}
        self._active: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._dedupe = timedelta(minutes=dedupe_minutes)

    def _public(self, record: Dict[str, Any]) -> Dict[str, Any]:
        status = advisor_status()
        if status["open"]:
            message = (
                f"Solicitud {record['request_id']} registrada. "
                "Un asesor continuará la conversación en el horario de atención actual."
            )
        elif status["next_opening_label"]:
            message = (
                f"Solicitud {record['request_id']} registrada para el próximo horario "
                f"de atención, {status['next_opening_label']}"
            )
        else:
            message = (
                f"Solicitud {record['request_id']} registrada. "
                "Se revisará cuando se reanude la atención."
            )
        return {
            "request_id": record["request_id"],
            "status": record["status"],
            "available": status["open"],
            "schedule": status["schedule"],
            "timezone": status["timezone"],
            "created_at": record["created_at"],
            "closing_at_label": status["closing_at_label"],
            "next_opening": status["next_opening"],
            "next_opening_label": status["next_opening_label"],
            "message": message,
        }

    def create(
        self,
        *,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        name: Optional[str] = None,
        city: Optional[str] = None,
        channel: str = "web",
        topic: str = "general",
        message: str = "",
        product_id: Optional[str] = None,
        product_name: Optional[str] = None,
        price: Optional[float] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        key = f"user:{user_id}" if user_id else (f"session:{session_id}" if session_id else "")
        with self._lock:
            if key:
                active_id = self._active.get(key)
                active = self._requests.get(active_id or "")
                if active:
                    created = datetime.fromisoformat(active["created_at"])
                    if now - created < self._dedupe:
                        return self._public(active)

            request_id = f"AS-{uuid.uuid4().hex[:6].upper()}"
            record = {
                "request_id": request_id,
                "status": "registrada",
                "topic": topic,
                "name": (name or "").strip()[:120],
                "city": (city or "").strip()[:80],
                "channel": channel,
                "message": (message or "").strip()[:2000],
                "product_id": product_id,
                "product_name": product_name,
                "price": int(price) if price else None,
                "user_id": user_id,
                "session_id": session_id,
                "created_at": now.isoformat(),
            }
            self._requests[request_id] = record
            if key:
                self._active[key] = request_id
            return self._public(record)


_store = AdvisorRequestStore()


def create_advisor_request(**kwargs: Any) -> Dict[str, Any]:
    """Registra una solicitud de asesoría y devuelve el handoff público."""
    return _store.create(**kwargs)
