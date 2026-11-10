"""Capa de acceso a datos.

`SnowflakeClient` encapsula la conexión a Snowflake y expone operaciones de
negocio (inventario, Customer 360 y score de crédito). Cuando no hay
credenciales configuradas, o cuando una consulta falla y `SNOWFLAKE_FALLBACK_DEMO`
está activo, se responde con el catálogo de demostración para no interrumpir la
experiencia del usuario.

Esquema esperado (ajustable mediante variables de entorno):

INVENTARIO_PRODUCTOS
  PRODUCT_ID, SKU, NOMBRE, CATEGORIA, SUBCATEGORIA, COLOR, COLOR_HEX, PRECIO,
  ANCHO_CM, PROFUNDIDAD_CM, ALTO_CM, MATERIAL, DESCRIPCION, IMAGEN, RATING,
  CIUDAD, STOCK

CUSTOMER_360
  USER_ID, NOMBRE, DOCUMENTO, CIUDAD, SEGMENTO, COMPRAS, TICKET_PROMEDIO,
  ULTIMA_COMPRA, CATEGORIAS_PREFERIDAS, INGRESO_MENSUAL, OBLIGACIONES_MENSUALES,
  SCORE_CREDITO, CUPO_CREDIJAMAR
"""

from __future__ import annotations

import logging
import re
import threading
import unicodedata
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Sequence

from catalog import (
    CITIES,
    CITY_NAMES,
    DEMO_PRODUCTS,
    demo_customer,
    public_product,
)
from config import get_settings

logger = logging.getLogger(__name__)

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")


def normalize_text(value: str) -> str:
    """Minúsculas y sin acentos para comparaciones tolerantes."""
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return without_accents.lower().strip()


def _safe_identifier(value: str, label: str) -> str:
    """Evita inyección de SQL en nombres de tabla configurables."""
    if not _IDENTIFIER_RE.match(value):
        raise ValueError(f"Identificador inválido para {label}: {value!r}")
    return value


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


class SnowflakeClient:
    """Cliente de datos con reconexión perezosa y modo demostración."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._connection = None
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Conexión
    # ------------------------------------------------------------------
    @property
    def configured(self) -> bool:
        return self.settings.snowflake_configured

    @property
    def mode(self) -> str:
        return "snowflake" if self.configured else "demo"

    def _connect(self):
        """Abre una conexión usando el conector oficial de Snowflake."""
        import snowflake.connector  # importación diferida

        params: Dict[str, Any] = {
            "account": self.settings.snowflake_account,
            "user": self.settings.snowflake_user,
            "password": self.settings.snowflake_password,
            "database": self.settings.snowflake_database,
            "schema": self.settings.snowflake_schema,
            "warehouse": self.settings.snowflake_warehouse,
            "paramstyle": "qmark",
            "client_session_keep_alive": True,
            "login_timeout": 15,
            "network_timeout": 30,
        }
        if self.settings.snowflake_role:
            params["role"] = self.settings.snowflake_role
        logger.info("Conectando a Snowflake (%s)", self.settings.snowflake_account)
        return snowflake.connector.connect(**params)

    def _get_connection(self):
        with self._lock:
            if self._connection is None or getattr(self._connection, "is_closed", lambda: True)():
                self._connection = self._connect()
            return self._connection

    def close(self) -> None:
        """Cierra la conexión activa, si existe."""
        with self._lock:
            if self._connection is not None:
                try:
                    self._connection.close()
                except Exception:  # pragma: no cover - cierre defensivo
                    logger.exception("Error cerrando conexión Snowflake")
                finally:
                    self._connection = None

    def _query(self, sql: str, params: Sequence[Any] = ()) -> List[Dict[str, Any]]:
        """Ejecuta una consulta y devuelve filas con claves en minúscula."""
        from snowflake.connector import DictCursor

        with self._lock:
            connection = self._get_connection()
            try:
                with connection.cursor(DictCursor) as cursor:
                    cursor.execute(sql, params)
                    rows = cursor.fetchall() or []
                    return [
                        {str(key).lower(): value for key, value in dict(row).items()}
                        for row in rows
                    ]
            except Exception:
                # Se invalida la conexión para permitir reconexión en la próxima llamada.
                try:
                    connection.close()
                except Exception:
                    pass
                self._connection = None
                raise

    def _table(self, name: str) -> str:
        database = _safe_identifier(self.settings.snowflake_database, "SNOWFLAKE_DATABASE")
        schema = _safe_identifier(self.settings.snowflake_schema, "SNOWFLAKE_SCHEMA")
        table = _safe_identifier(name, "tabla")
        return f"{database}.{schema}.{table}"

    # ------------------------------------------------------------------
    # Inventario / productos
    # ------------------------------------------------------------------
    def _demo_filter(
        self,
        products: Iterable[Dict[str, Any]],
        city: Optional[str] = None,
        category: Optional[str] = None,
        color: Optional[str] = None,
        max_price: Optional[float] = None,
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        city_norm = normalize_text(city or "")
        category_norm = normalize_text(category or "")
        color_norm = normalize_text(color or "")
        query_norm = normalize_text(query or "")
        results: List[Dict[str, Any]] = []

        for product in products:
            stock = product.get("stock_by_city", {})
            if city and _as_int(stock.get(city, 0)) <= 0:
                continue
            if category_norm and category_norm not in normalize_text(product.get("category", "")):
                if category_norm not in normalize_text(product.get("subcategory", "")):
                    continue
            if color_norm and color_norm not in normalize_text(product.get("color", "")):
                continue
            if max_price is not None and _as_float(product.get("price", 0)) > max_price:
                continue
            if query_norm:
                haystack = normalize_text(
                    " ".join(
                        [
                            product.get("name", ""),
                            product.get("category", ""),
                            product.get("subcategory", ""),
                            product.get("description", ""),
                            product.get("color", ""),
                            " ".join(product.get("tags", [])),
                        ]
                    )
                )
                tokens = [token for token in query_norm.split() if len(token) > 2]
                if tokens and not any(token in haystack for token in tokens):
                    continue
            results.append(product)

        results.sort(key=lambda item: (-_as_int(item.get("rating", 0) * 10), item.get("price", 0)))
        return results

    def list_products(
        self,
        city: Optional[str] = None,
        category: Optional[str] = None,
        color: Optional[str] = None,
        max_price: Optional[float] = None,
        query: Optional[str] = None,
        limit: int = 12,
    ) -> List[Dict[str, Any]]:
        """Busca productos en inventario aplicando filtros opcionales."""
        limit = max(1, min(int(limit), 50))

        if not self.configured:
            demo = self._demo_filter(DEMO_PRODUCTS, city, category, color, max_price, query)
            return [public_product(item, city) for item in demo[:limit]]

        where: List[str] = ["STOCK > 0"]
        params: List[Any] = []
        if city:
            where.append("UPPER(CIUDAD) = UPPER(?)")
            params.append(city)
        if category:
            where.append("(UPPER(CATEGORIA) LIKE UPPER(?) OR UPPER(SUBCATEGORIA) LIKE UPPER(?))")
            params.extend([f"%{category}%", f"%{category}%"])
        if color:
            where.append("UPPER(COLOR) LIKE UPPER(?)")
            params.append(f"%{color}%")
        if max_price is not None:
            where.append("PRECIO <= ?")
            params.append(float(max_price))
        if query:
            where.append(
                "(UPPER(NOMBRE) LIKE UPPER(?) OR UPPER(DESCRIPCION) LIKE UPPER(?) "
                "OR UPPER(MATERIAL) LIKE UPPER(?))"
            )
            like = f"%{query}%"
            params.extend([like, like, like])

        sql = f"""
            SELECT PRODUCT_ID, SKU, NOMBRE, CATEGORIA, SUBCATEGORIA, COLOR, COLOR_HEX,
                   PRECIO, ANCHO_CM, PROFUNDIDAD_CM, ALTO_CM, MATERIAL, DESCRIPCION,
                   IMAGEN, RATING, CIUDAD, STOCK
            FROM {self._table(self.settings.snowflake_inventory_table)}
            WHERE {' AND '.join(where)}
            QUALIFY ROW_NUMBER() OVER (PARTITION BY PRODUCT_ID ORDER BY STOCK DESC) <= 60
        """
        try:
            rows = self._query(sql, params)
            products = self._map_inventory_rows(rows)
            products.sort(
                key=lambda item: (
                    -_as_float(item.get("rating", 0)),
                    _as_int(item.get("price", 0)),
                )
            )
            return [public_product(item, city) for item in products[:limit]]
        except Exception:
            logger.exception("Consulta de inventario fallida; se activa modo demostración")
            if not self.settings.snowflake_fallback_demo:
                raise
            demo = self._demo_filter(DEMO_PRODUCTS, city, category, color, max_price, query)
            return [public_product(item, city) for item in demo[:limit]]

    def _map_inventory_rows(self, rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Agrupa filas por producto y consolida el inventario por ciudad."""
        grouped: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            product_id = str(row.get("product_id") or row.get("id") or "").strip()
            if not product_id:
                continue
            city = str(row.get("ciudad") or "").strip()
            stock = _as_int(row.get("stock", 0))

            if product_id not in grouped:
                grouped[product_id] = {
                    "id": product_id,
                    "sku": row.get("sku") or product_id,
                    "name": row.get("nombre") or row.get("name") or "Producto Jamar",
                    "category": row.get("categoria") or "",
                    "subcategory": row.get("subcategoria") or row.get("subcategory") or "",
                    "color": row.get("color") or "",
                    "color_hex": row.get("color_hex") or "#B9B4A8",
                    "price": _as_int(row.get("precio") or row.get("price")),
                    "width_cm": _as_int(row.get("ancho_cm")),
                    "depth_cm": _as_int(row.get("profundidad_cm")),
                    "height_cm": _as_int(row.get("alto_cm")),
                    "material": row.get("material") or "",
                    "description": row.get("descripcion") or row.get("description") or "",
                    "image": row.get("imagen") or row.get("image") or "sofa.png",
                    "rating": _as_float(row.get("rating"), 4.5),
                    "tags": [],
                    "stock_by_city": {},
                }
            if city:
                grouped[product_id]["stock_by_city"][city] = (
                    grouped[product_id]["stock_by_city"].get(city, 0) + stock
                )
        return list(grouped.values())

    def get_product(self, product_id: str, city: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Recupera un producto por identificador."""
        if not self.configured:
            for item in DEMO_PRODUCTS:
                if item["id"] == product_id:
                    return public_product(item, city)
            return None

        sql = f"""
            SELECT PRODUCT_ID, SKU, NOMBRE, CATEGORIA, SUBCATEGORIA, COLOR, COLOR_HEX,
                   PRECIO, ANCHO_CM, PROFUNDIDAD_CM, ALTO_CM, MATERIAL, DESCRIPCION,
                   IMAGEN, RATING, CIUDAD, STOCK
            FROM {self._table(self.settings.snowflake_inventory_table)}
            WHERE PRODUCT_ID = ?
        """
        try:
            rows = self._query(sql, [product_id])
            products = self._map_inventory_rows(rows)
            return public_product(products[0], city) if products else None
        except Exception:
            logger.exception("Consulta de producto fallida; se activa modo demostración")
            if not self.settings.snowflake_fallback_demo:
                raise
            for item in DEMO_PRODUCTS:
                if item["id"] == product_id:
                    return public_product(item, city)
            return None

    def inventory_summary(self) -> Dict[str, Any]:
        """Resumen consolidado de inventario por categoría."""
        products = self.list_products(limit=50)
        categories: Dict[str, int] = {}
        total_units = 0
        for product in products:
            total_units += _as_int(product.get("stock", 0))
            category = product.get("category") or "Otros"
            categories[category] = categories.get(category, 0) + _as_int(product.get("stock", 0))
        return {
            "total_products": len(products),
            "total_units": total_units,
            "categories": categories,
            "cities": CITY_NAMES,
        }

    def cities(self) -> List[Dict[str, Any]]:
        """Ciudades con cobertura comercial."""
        return list(CITIES)

    # ------------------------------------------------------------------
    # Customer 360 y crédito
    # ------------------------------------------------------------------
    def get_customer(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Consulta el perfil Customer 360 y el score de crédito del cliente."""
        if not user_id:
            return None
        if not self.configured:
            return demo_customer(user_id)

        sql = f"""
            SELECT USER_ID, NOMBRE, DOCUMENTO, CIUDAD, SEGMENTO, COMPRAS,
                   TICKET_PROMEDIO, ULTIMA_COMPRA, CATEGORIAS_PREFERIDAS,
                   INGRESO_MENSUAL, OBLIGACIONES_MENSUALES, SCORE_CREDITO,
                   CUPO_CREDIJAMAR
            FROM {self._table(self.settings.snowflake_customer_table)}
            WHERE USER_ID = ?
            LIMIT 1
        """
        try:
            rows = self._query(sql, [user_id])
            if not rows:
                return demo_customer(user_id)
            row = rows[0]
            preferred = row.get("categorias_preferidas")
            if isinstance(preferred, str):
                preferred = [item.strip() for item in preferred.split(",") if item.strip()]
            score = _as_int(row.get("score_credito"), 700)
            return {
                "user_id": str(row.get("user_id") or user_id),
                "name": row.get("nombre") or "Cliente Jamar",
                "document": row.get("documento") or "",
                "city": row.get("ciudad") or "",
                "segment": row.get("segmento") or "",
                "purchases": _as_int(row.get("compras")),
                "avg_ticket": _as_int(row.get("ticket_promedio")),
                "last_purchase": str(row.get("ultima_compra")) if row.get("ultima_compra") else None,
                "preferred_categories": preferred or [],
                "monthly_income": _as_int(row.get("ingreso_mensual")),
                "monthly_obligations": _as_int(row.get("obligaciones_mensuales")),
                "credit_score": score,
                "credi_jamar_limit": _as_int(
                    row.get("cupo_credijamar"),
                    credit_limit_from_catalog(score),
                ),
            }
        except Exception:
            logger.exception("Consulta Customer 360 fallida; se activa modo demostración")
            if not self.settings.snowflake_fallback_demo:
                raise
            return demo_customer(user_id)


def credit_limit_from_catalog(score: int) -> int:
    """Alias local para evitar un import circular en tiempo de ejecución."""
    from catalog import credit_limit_for_score

    return credit_limit_for_score(score)


@lru_cache(maxsize=1)
def get_snowflake_client() -> SnowflakeClient:
    """Singleton del cliente de datos."""
    return SnowflakeClient()
