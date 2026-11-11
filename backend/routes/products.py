"""Endpoints de catálogo e inventario."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from schemas import InventorySummary, Product
from snowflake_client import get_snowflake_client

router = APIRouter(tags=["Catálogo"])


@router.get("/products", response_model=List[Product], summary="Busca productos en inventario")
def list_products(
    city: Optional[str] = Query(default=None, description="Ciudad de entrega"),
    category: Optional[str] = Query(default=None, description="Categoría o subcategoría"),
    color: Optional[str] = Query(default=None, description="Color del producto"),
    max_price: Optional[float] = Query(default=None, ge=0, description="Presupuesto máximo en COP"),
    q: Optional[str] = Query(default=None, description="Texto libre"),
    limit: int = Query(default=12, ge=1, le=50),
) -> List[Product]:
    """Filtra el inventario por ciudad, categoría, color y presupuesto."""
    items = get_snowflake_client().list_products(
        city=city,
        category=category,
        color=color,
        max_price=max_price,
        query=q,
        limit=limit,
    )
    return [Product(**item) for item in items]


@router.get("/products/{product_id}", response_model=Product, summary="Detalle de producto")
def get_product(
    product_id: str,
    city: Optional[str] = Query(default=None),
) -> Product:
    """Entrega la ficha completa de un producto e inventario por ciudad."""
    item = get_snowflake_client().get_product(product_id, city=city)
    if not item:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return Product(**item)


@router.get("/inventory/summary", response_model=InventorySummary, summary="Resumen de inventario")
def inventory_summary() -> InventorySummary:
    """Consolida unidades disponibles por categoría y ciudad."""
    return InventorySummary(**get_snowflake_client().inventory_summary())


@router.get("/cities", summary="Ciudades con cobertura")
def cities() -> dict:
    """Lista las ciudades donde opera Jamar con número de tiendas."""
    return {"cities": get_snowflake_client().cities()}
