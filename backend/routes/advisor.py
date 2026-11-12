"""Endpoints de disponibilidad y solicitudes de asesoría."""

from __future__ import annotations

from fastapi import APIRouter

from advisor import advisor_status, create_advisor_request
from schemas import AdvisorHandoff, AdvisorRequestBody, AdvisorStatus

router = APIRouter(tags=["Asesoría"])


@router.get("/advisor/status", response_model=AdvisorStatus, summary="Horario y disponibilidad de asesoría")
def status() -> AdvisorStatus:
    """Indica si hay asesores disponibles y cuándo vuelve a abrir el horario."""
    return AdvisorStatus(**advisor_status())


@router.post("/advisor/request", response_model=AdvisorHandoff, summary="Registra una solicitud de asesoría")
def request(payload: AdvisorRequestBody) -> AdvisorHandoff:
    """Crea o reutiliza una solicitud reciente para el mismo usuario o sesión."""
    handoff = create_advisor_request(**payload.model_dump())
    return AdvisorHandoff(**handoff)
