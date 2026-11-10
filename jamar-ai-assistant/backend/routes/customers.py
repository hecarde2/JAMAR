"""Endpoints de Customer 360."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from schemas import CustomerProfile
from snowflake_client import get_snowflake_client

router = APIRouter(tags=["Customer 360"])


@router.get("/customer/{user_id}", response_model=CustomerProfile, summary="Perfil Customer 360")
def get_customer(user_id: str) -> CustomerProfile:
    """Recupera el perfil analítico del cliente para personalizar la asesoría."""
    customer = get_snowflake_client().get_customer(user_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return CustomerProfile(**customer)
