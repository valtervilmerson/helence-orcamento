"""Schemas Pydantic do catálogo manual (docs/06, seções 14.8/14.9)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

FinishGroup = Literal["madeirado", "metalico", "pe_estrutura", "outro"]


# ---------------------------------------------------------------------------
# Famílias de produto
# ---------------------------------------------------------------------------


class ProductFamilyIn(BaseModel):
    name: str
    description: str | None = None


class ProductFamilyPatch(BaseModel):
    name: str | None = None
    description: str | None = None


class ProductFamilyOut(ProductFamilyIn):
    id: int


# ---------------------------------------------------------------------------
# Dimensões
# ---------------------------------------------------------------------------


class DimensionIn(BaseModel):
    width_mm: int | None = None
    depth_mm: int | None = None
    diameter_mm: int | None = None
    height_mm: int | None = None
    raw_label: str | None = None


class DimensionPatch(BaseModel):
    width_mm: int | None = None
    depth_mm: int | None = None
    diameter_mm: int | None = None
    height_mm: int | None = None
    raw_label: str | None = None


class DimensionOut(DimensionIn):
    id: int


# ---------------------------------------------------------------------------
# Acabamentos
# ---------------------------------------------------------------------------


class FinishIn(BaseModel):
    name: str
    finish_group: FinishGroup | None = None
    description: str | None = None


class FinishPatch(BaseModel):
    name: str | None = None
    finish_group: FinishGroup | None = None
    description: str | None = None


class FinishOut(FinishIn):
    id: int


# ---------------------------------------------------------------------------
# Tipos de componente
# ---------------------------------------------------------------------------


class ProductComponentIn(BaseModel):
    name: str
    description: str | None = None


class ProductComponentPatch(BaseModel):
    name: str | None = None
    description: str | None = None


class ProductComponentOut(ProductComponentIn):
    id: int


# ---------------------------------------------------------------------------
# Produtos-base
# ---------------------------------------------------------------------------


class ProductIn(BaseModel):
    family_id: int
    name: str
    dimension_id: int | None = None


class ProductPatch(BaseModel):
    family_id: int | None = None
    name: str | None = None
    dimension_id: int | None = None


class ProductOut(ProductIn):
    id: int


# ---------------------------------------------------------------------------
# Variações vendáveis (component_variants + sku + price) — 14.9
# ---------------------------------------------------------------------------


class SkuIn(BaseModel):
    code: str
    notes: str | None = None


class PriceIn(BaseModel):
    amount: float = Field(ge=0)
    currency: str = "BRL"
    price_table_id: int


class ComponentVariantIn(BaseModel):
    product_id: int | None = None
    component_id: int
    dimension_id: int | None = None
    finish_id: int | None = None
    descriptor: str | None = None
    description: str | None = None
    sku: SkuIn | None = None
    price: PriceIn | None = None


class ComponentVariantPatch(BaseModel):
    product_id: int | None = None
    component_id: int | None = None
    dimension_id: int | None = None
    finish_id: int | None = None
    descriptor: str | None = None
    description: str | None = None


class DimensionSummary(BaseModel):
    width_mm: int | None = None
    depth_mm: int | None = None
    diameter_mm: int | None = None
    height_mm: int | None = None
    raw_label: str | None = None


class PriceSummary(BaseModel):
    amount: float
    currency: str


class PriceTableSummary(BaseModel):
    id: int
    code: str
    status: str


class PriceHistoryEntry(BaseModel):
    price_table: PriceTableSummary
    price: PriceSummary


class ComponentVariantOut(BaseModel):
    component_variant_id: int
    family: str | None = None
    product: str | None = None
    component: str
    descriptor: str | None = None
    description: str | None = None
    dimension: DimensionSummary | None = None
    finish: str | None = None
    sku: str | None = None
    price: PriceSummary | None = None
    price_table: PriceTableSummary | None = None
    source: str = "cadastro_manual"
    price_history: list[PriceHistoryEntry] | None = None


class ComponentVariantSearchResult(BaseModel):
    items: list[ComponentVariantOut]
    page: int
    page_size: int
    total: int
