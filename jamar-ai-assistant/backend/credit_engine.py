"""Motor financiero de CrediJamar.

Calcula la cuota semanal mediante amortización francesa, estima la capacidad
de pago del cliente y determina el estado de pre-aprobación. El motor es
determinista y no escribe en Snowflake: la solicitud formal se gestiona con un asesor.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

from catalog import credit_limit_for_score
from config import get_settings

TERM_OPTIONS: List[int] = [8, 12, 16, 24, 36, 52]


def weekly_payment(principal: float, weekly_rate: float, weeks: int) -> float:
    """Cuota semanal bajo amortización francesa."""
    if weeks <= 0:
        return 0.0
    if weekly_rate <= 0:
        return principal / weeks
    factor = math.pow(1 + weekly_rate, weeks)
    return principal * weekly_rate * factor / (factor - 1)


def max_principal_from_payment(payment: float, weekly_rate: float, weeks: int) -> float:
    """Capital máximo financiable dada una cuota semanal máxima."""
    if weeks <= 0 or payment <= 0:
        return 0.0
    if weekly_rate <= 0:
        return payment * weeks
    factor = math.pow(1 + weekly_rate, weeks)
    return payment * (factor - 1) / (weekly_rate * factor)


def _status_for(approved: bool, score: int, requires_review: bool) -> str:
    if approved:
        return "pre_aprobado"
    if requires_review:
        return "requiere_validacion"
    return "no_aprobado"


def _reason(
    approved: bool,
    requires_review: bool,
    requested: float,
    max_amount: float,
    weekly_payment_value: float,
    weekly_capacity: float,
    score: int,
) -> str:
    if approved:
        return (
            "Tu perfil cumple con las políticas de CrediJamar. Puedes continuar con la "
            "solicitud y un asesor confirmará la aprobación definitiva."
        )
    if requires_review:
        return (
            "El monto solicitado supera tu cupo pre-aprobado. Un asesor puede revisar "
            "documentos adicionales para ampliar la evaluación."
        )
    if weekly_payment_value > weekly_capacity:
        return (
            "La cuota semanal estimada supera tu capacidad de pago disponible. "
            "Puedes aumentar la cuota inicial o ampliar el plazo."
        )
    if requested > max_amount:
        return (
            f"El monto financiado solicitado supera tu cupo disponible de "
            f"{max_amount:,.0f} COP. Considera una cuota inicial mayor o un plazo más amplio."
        ).replace(",", ".")
    return (
        "En este momento no es posible pre-aprobar la compra con la información disponible. "
        "Un asesor CrediJamar puede revisar tu caso."
    )


def simulate_credit(
    price: float,
    down_payment: float,
    term_weeks: int,
    customer: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Calcula la oferta CrediJamar para un producto y un cliente."""
    settings = get_settings()
    customer = customer or {}
    score = int(customer.get("credit_score", 700) or 700)

    price = max(float(price), 1.0)
    max_term_weeks = int(
        max(4, min(settings.credit_max_term_weeks, max(TERM_OPTIONS)))
    )
    term_weeks = int(max(4, min(term_weeks, max_term_weeks)))
    min_down_payment = round(price * settings.credit_min_down_payment_pct)
    down_payment = max(float(down_payment), float(min_down_payment))
    down_payment = min(down_payment, price)
    financed = max(price - down_payment, 0.0)

    weekly_rate = float(settings.credit_weekly_rate)
    pmt = weekly_payment(financed, weekly_rate, term_weeks)
    monthly = pmt * 52 / 12
    total_to_pay = pmt * term_weeks + down_payment
    total_interest = max(total_to_pay - price, 0.0)
    annual_effective = math.pow(1 + weekly_rate, 52) - 1

    # Capacidad de pago: 30% del ingreso disponible después de obligaciones.
    monthly_income = float(customer.get("monthly_income", 3_000_000) or 3_000_000)
    obligations = float(customer.get("monthly_obligations", 0) or 0)
    monthly_capacity = max(monthly_income * 0.30 - obligations, monthly_income * 0.10)
    weekly_capacity = monthly_capacity * 12 / 52

    score_limit = float(customer.get("credi_jamar_limit") or credit_limit_for_score(score))
    income_limit = max_principal_from_payment(weekly_capacity, weekly_rate, term_weeks)
    max_amount = int(max(min(score_limit, income_limit), 0))

    approved = (
        score >= 650
        and financed <= max_amount
        and pmt <= weekly_capacity
        and financed > 0
    )
    requires_review = (not approved) and score >= 620 and financed <= score_limit * 1.35

    return {
        "approved": approved,
        "status": _status_for(approved, score, requires_review),
        "approved_amount": int(min(financed, max_amount)) if approved else 0,
        "max_amount": max_amount,
        "price": int(round(price)),
        "down_payment": int(round(down_payment)),
        "financed_amount": int(round(financed)),
        "term_weeks": term_weeks,
        "weekly_rate": weekly_rate,
        "weekly_payment": int(round(pmt)),
        "monthly_payment": int(round(monthly)),
        "total_interest": int(round(total_interest)),
        "total_to_pay": int(round(total_to_pay)),
        "annual_effective_rate": round(annual_effective, 4),
        "credit_score": score,
        "customer_name": customer.get("name", "Cliente Jamar"),
        "reason": _reason(
            approved,
            requires_review,
            financed,
            max_amount,
            pmt,
            weekly_capacity,
            score,
        ),
    }


def credit_options() -> Dict[str, Any]:
    """Parámetros públicos para el simulador del frontend."""
    settings = get_settings()
    max_term_weeks = int(
        max(4, min(settings.credit_max_term_weeks, max(TERM_OPTIONS)))
    )
    term_options = [term for term in TERM_OPTIONS if term <= max_term_weeks]
    return {
        "term_options": term_options or [max_term_weeks],
        "weekly_rate": settings.credit_weekly_rate,
        "min_down_payment_pct": settings.credit_min_down_payment_pct,
        "currency": "COP",
    }
