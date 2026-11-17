"""Composición de un producto del catálogo sobre la foto de un espacio."""

from __future__ import annotations

import io
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image, ImageFilter

from product_images import load_product_rgba, load_room_image
from snowflake_client import get_snowflake_client

router = APIRouter(tags=["Composición"])

MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}


@router.post("/compose", summary="Superpone un producto sobre la foto del espacio")
async def compose_product(
    file: UploadFile = File(..., description="Fotografía del espacio"),
    product_id: Optional[str] = Form(default=None),
    product_image: Optional[str] = Form(default=None),
    x: float = Form(default=50, ge=0, le=100, description="Posición horizontal en porcentaje"),
    y: float = Form(default=70, ge=0, le=100, description="Posición vertical en porcentaje"),
    scale: float = Form(default=0.45, ge=0.05, le=2, description="Ancho del mueble respecto a la foto"),
    rotation: float = Form(default=0, ge=-180, le=180, description="Rotación en grados"),
) -> Response:
    """Devuelve un PNG con el mueble ubicado en la posición indicada."""
    if file.content_type and file.content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Formato no soportado. Usa JPG, PNG o WEBP.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="No se recibió ninguna imagen.")
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="La imagen supera el límite de 8 MB.")

    if product_id:
        item = get_snowflake_client().get_product(product_id)
        if not item:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        filename = item.get("image") or "sofa.png"
    elif product_image:
        filename = product_image
    else:
        raise HTTPException(status_code=400, detail="Indica product_id o product_image")

    room = load_room_image(content)
    product = load_product_rgba(filename)

    target_width = max(1, int(room.width * scale))
    product.thumbnail((target_width, room.height * 2), Image.Resampling.LANCZOS)
    if rotation:
        product = product.rotate(
            rotation,
            resample=Image.Resampling.BICUBIC,
            expand=True,
            fillcolor=(0, 0, 0, 0),
        )

    center_x = room.width * x / 100
    center_y = room.height * y / 100
    left = int(center_x - product.width / 2)
    top = int(center_y - product.height / 2)

    shadow_mask = Image.new("L", room.size, 0)
    shadow_mask.paste(product.getchannel("A"), (left + 4, top + max(5, room.height // 90)))
    shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(max(4, room.width // 90)))
    room.paste((18, 18, 18, 105), (0, 0, room.width, room.height), shadow_mask)

    room.alpha_composite(product, (left, top))

    output = io.BytesIO()
    room.convert("RGB").save(output, format="PNG", optimize=True)
    return Response(
        content=output.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )
