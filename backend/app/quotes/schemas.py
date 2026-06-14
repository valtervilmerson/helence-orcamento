"""Schemas Pydantic do ciclo de vida básico de orçamentos (docs/06, 14.10-14.13)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

QuoteStatus = Literal["rascunho", "enviado", "aprovado", "rejeitado", "expirado"]


# ---------------------------------------------------------------------------
# Orçamento — 14.10
# ---------------------------------------------------------------------------


class QuoteCreateIn(BaseModel):
    customer_id: int
    valid_until: str | None = None
    notes: str | None = None


class CustomerSummary(BaseModel):
    id: int
    name: str


class CustomerCreateIn(BaseModel):
    name: str
    document: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None


class UserSummary(BaseModel):
    id: int
    name: str


class QuoteOut(BaseModel):
    id: int
    quote_number: str
    status: QuoteStatus
    customer: CustomerSummary
    created_by: UserSummary | None = None
    created_at: str
    valid_until: str | None = None
    notes: str | None = None
    source_quote_id: int | None = None


# ---------------------------------------------------------------------------
# Itens — 14.11/14.12 (forma simplificada: um único componente por item)
# ---------------------------------------------------------------------------


class QuoteItemComponentInput(BaseModel):
    component_variant_id: int


class QuoteItemCreateIn(BaseModel):
    label: str
    product_id: int | None = None
    quantity: int = Field(default=1, gt=0)
    notes: str | None = None
    # Forma simplificada (Fase 3, retrocompatível) ou composição completa
    # (Fase 9, docs/06 §14.11) — exatamente um dos dois deve ser informado.
    component_variant_id: int | None = None
    components: list[QuoteItemComponentInput] | None = None


class QuoteItemComponentCreateIn(BaseModel):
    component_variant_id: int


class QuoteItemComponentSwapIn(BaseModel):
    component_variant_id: int


class QuoteItemComponentSwapOut(BaseModel):
    id: int
    component_variant_id: int
    sku: str | None = None
    previous_frozen_unit_price: float
    frozen_unit_price: float
    frozen_currency: str
    frozen_at: str
    price_changed: bool


class QuoteItemPatchIn(BaseModel):
    quantity: int | None = None
    discount_percent: float | None = None
    discount_amount: float | None = None
    discount_reason: str | None = None
    notes: str | None = None
    composition_justification: str | None = None


class QuoteItemComponentOut(BaseModel):
    id: int
    component_variant_id: int
    sku: str | None = None
    frozen_unit_price: float
    frozen_currency: str
    frozen_at: str


class QuoteItemOut(BaseModel):
    id: int
    quote_id: int
    label: str
    quantity: int
    discount_percent: float | None = None
    discount_amount: float | None = None
    discount_reason: str | None = None
    notes: str | None = None
    composition_justification: str | None = None
    missing_required_components: list[str] = []
    pricing_pendencias: list[str] = []
    components: list[QuoteItemComponentOut]
    line_subtotal: float


# ---------------------------------------------------------------------------
# Status — mudança de etapa do ciclo de vida
# ---------------------------------------------------------------------------


class QuoteStatusPatchIn(BaseModel):
    status: QuoteStatus


# ---------------------------------------------------------------------------
# Checklist de revisão final — RN-18 (docs/05)
# ---------------------------------------------------------------------------


class QuoteReviewChecklistItem(BaseModel):
    code: str
    label: str
    ok: bool
    pendencias: list[str] = []


class QuoteReviewChecklistOut(BaseModel):
    quote_id: int
    ready: bool
    items: list[QuoteReviewChecklistItem]


# ---------------------------------------------------------------------------
# Totais — 14.13
# ---------------------------------------------------------------------------


class QuoteTotalWarning(BaseModel):
    code: str
    message: str


class QuoteTotalsOut(BaseModel):
    quote_id: int
    subtotal: float
    discount_percent: float
    discount_amount: float
    tax_amount: float
    freight_amount: float
    total: float
    currency: str
    is_snapshot: bool
    calculated_at: str
    warnings: list[QuoteTotalWarning]
