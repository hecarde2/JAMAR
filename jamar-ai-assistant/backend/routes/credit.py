"""Endpoints de simulación y pre-aprobación CrediJamar."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from catalog import demo_customer
from credit_engine import credit_options, simulate_credit
from schemas import CreditOffer, CreditSimulationRequest
from snowflake_client import get_snowflake_client

router = APIRouter(tags=["CrediJamar"])


@router.post("/credit-check", response_model=CreditOffer, summary="Simula y pre-aprueba crédito")
def credit_check(payload: CreditSimulationRequest) -> CreditOffer:
    """Calcula cuota semanal/mensual y evalúa la pre-aprobación en tiempo real."""
    try:
        repository = get_snowflake_client()
        customer = repository.get_customer(payload.user_id) if payload.user_id else demo_customer("invitado-jamar")
        offer = simulate_credit(
            price=payload.price,
            down_payment=payload.down_payment,
            term_weeks=payload.term_weeks,
            customer=customer,
        )
        return CreditOffer(**offer)
    except Exception as exc:  # pragma: no cover - protección de borde
        raise HTTPException(status_code=500, detail="No fue posible calcular la simulación") from exc


@router.get("/credit/preapproval/{user_id}", summary="Consulta el cupo pre-aprobado del cliente")
def preapproval(user_id: str) -> dict:
    """Devuelve el perfil financiero resumido y el cupo máximo pre-aprobado."""
    customer = get_snowflake_client().get_customer(user_id) or demo_customer(user_id)
    return {
        "user_id": user_id,
        "customer_name": customer.get("name"),
        "credit_score": customer.get("credit_score"),
        "max_amount": customer.get("credi_jamar_limit"),
        "city": customer.get("city"),
        "options": credit_options(),
    }


@router.get("/credit/config", summary="Parámetros públicos del simulador")
def config() -> dict:
    """Expone plazos y tasa semanal usados por el frontend."""
    return credit_options()
