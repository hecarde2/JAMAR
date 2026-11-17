"""Carga y preparación de las imágenes del catálogo para composición."""

from __future__ import annotations

import io
import re
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from config import get_settings

SAFE_IMAGE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*\.(?:png|jpg|jpeg|webp)$", re.IGNORECASE)
MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def resolve_product_image_path(filename: str) -> Path:
    if not SAFE_IMAGE_NAME.match(filename or ""):
        raise HTTPException(status_code=400, detail="Nombre de imagen de producto no válido")

    root = Path(get_settings().product_images_dir).expanduser().resolve()
    path = (root / filename).resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(status_code=404, detail="Imagen del producto no disponible")
    return path


def product_image_media_type(path: Path) -> str:
    return MEDIA_TYPES.get(path.suffix.lower(), "image/png")


def _remove_solid_background(image: Image.Image) -> Image.Image:
    rgba = ImageOps.exif_transpose(image).convert("RGBA")
    width, height = rgba.size
    background = rgba.getpixel((0, 0))[:3]
    marker = (255, 0, 255, 255)
    seeds = {(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)}
    seeds.update((x, 0) for x in range(0, width, 40))
    seeds.update((x, height - 1) for x in range(0, width, 40))
    seeds.update((0, y) for y in range(0, height, 40))
    seeds.update((width - 1, y) for y in range(0, height, 40))

    for seed in seeds:
        pixel = rgba.getpixel(seed)
        if all(abs(a - b) <= 30 for a, b in zip(pixel[:3], background)):
            ImageDraw.floodfill(rgba, seed, marker, thresh=30)

    mask = Image.new("L", rgba.size, 255)
    source = rgba.load()
    target = mask.load()
    for y in range(height):
        for x in range(width):
            if source[x, y][:3] == marker[:3]:
                target[x, y] = 0

    rgba.putalpha(mask.filter(ImageFilter.GaussianBlur(0.6)))
    return rgba


def load_product_rgba(filename: str) -> Image.Image:
    path = resolve_product_image_path(filename)
    cutout = path.with_name(f"{path.stem}-cutout{path.suffix}")
    if cutout.is_file():
        with Image.open(cutout) as image:
            image.load()
            return ImageOps.exif_transpose(image).convert("RGBA")

    with Image.open(path) as image:
        image.load()
        return _remove_solid_background(image)


def load_room_image(content: bytes) -> Image.Image:
    try:
        with Image.open(io.BytesIO(content)) as image:
            image.load()
            return ImageOps.exif_transpose(image).convert("RGBA")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="La imagen del espacio no es válida") from exc
