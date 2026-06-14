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
    finish_group: FinishGroup | None = None


class ProductComponentPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    finish_group: FinishGroup | None = None


class ProductComponentOut(ProductComponentIn):
    id: int


# ---------------------------------------------------------------------------
# Regras de compatibilidade entre componentes (RN-04)
# ---------------------------------------------------------------------------


class CompatibilityRuleIn(BaseModel):
    component_a_id: int
    descriptor_a: str
    component_b_id: int
    descriptor_b: str
    notes: str | None = None


class CompatibilityRulePatch(BaseModel):
    component_a_id: int | None = None
    descriptor_a: str | None = None
    component_b_id: int | None = None
    descriptor_b: str | None = None
    notes: str | None = None


class CompatibilityRuleOut(CompatibilityRuleIn):
    id: int


# ---------------------------------------------------------------------------
# Composição mínima por família (RN-07)
# ---------------------------------------------------------------------------

ComponentRequirement = Literal["obrigatorio", "opcional"]


class FamilyComponentRequirementIn(BaseModel):
    family_id: int
    component_id: int
    requirement: ComponentRequirement


class FamilyComponentRequirementPatch(BaseModel):
    family_id: int | None = None
    component_id: int | None = None
    requirement: ComponentRequirement | None = None


class FamilyComponentRequirementOut(FamilyComponentRequirementIn):
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


class ComponentVariantOut(BaseModel):
    component_variant_id: int
    family_id: int | None = None
    family: str | None = None
    product: str | None = None
    component: str
    descriptor: str | None = None
    description: str | None = None
    dimension: DimensionSummary | None = None
    finish: str | None = None
    finish_group: FinishGroup | None = None
    sku: str | None = None
    price: PriceSummary | None = None
    source: str = "cadastro_manual"


class ComponentVariantSearchResult(BaseModel):
    items: list[ComponentVariantOut]
    page: int
    page_size: int
    total: int


# ---------------------------------------------------------------------------
# Publicação de importação (docs/06, seção 14.7; docs/07, Fase 7)
# ---------------------------------------------------------------------------


class PublishIn(BaseModel):
    confirm: bool = False


class PublishOut(BaseModel):
    imported_file_id: int
    items_published: int
