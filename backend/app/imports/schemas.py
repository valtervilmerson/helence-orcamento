"""Modelos de request/response de importações (docs/06, seções 14.1-14.6)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.catalog.schemas import FinishGroup
from app.quotes.schemas import UserSummary

ImportStatus = Literal["recebido", "processando", "concluido", "erro"]
ReviewStatus = Literal["pendente", "revisado", "aprovado", "rejeitado", "corrigido"]
ConfidenceLevel = Literal["alta", "media", "baixa"]
ReviewDecisionType = Literal["aprovado", "rejeitado", "corrigido"]


class ImportedFileOut(BaseModel):
    id: int
    original_filename: str | None
    file_hash: str | None
    page_count: int | None
    status: ImportStatus
    imported_at: str
    imported_by: UserSummary | None
    notes: str | None = None


class ImportListItem(BaseModel):
    id: int
    original_filename: str | None
    status: ImportStatus
    page_count: int | None
    imported_at: str
    items_extracted: int
    items_pending_review: int
    items_blocking_publication: int


class ImportListOut(BaseModel):
    items: list[ImportListItem]
    page: int
    page_size: int
    total: int


class ProcessImportIn(BaseModel):
    strategy: str | None = None


class ProcessImportOut(BaseModel):
    id: int
    status: ImportStatus
    started_at: str | None


class ImportProgress(BaseModel):
    pages_total: int | None
    pages_processed: int | None


class ImportSummary(BaseModel):
    items_extracted: int
    warnings: int


class ImportError(BaseModel):
    code: str
    message: str


class ImportStatusOut(BaseModel):
    id: int
    status: ImportStatus
    progress: ImportProgress
    started_at: str | None
    finished_at: str | None
    summary: ImportSummary
    error: ImportError | None


# ---------------------------------------------------------------------------
# Itens extraídos e revisão (docs/06, 14.5/14.6; docs/07, Fase 6)
# ---------------------------------------------------------------------------


class ExtractedItemOut(BaseModel):
    id: int
    imported_page_id: int
    page_number: int
    family_raw: str | None
    product_context_raw: str | None
    component_type_raw: str | None
    description_raw: str | None
    dimension_raw: str | None
    finish_raw: str | None
    sku_raw: str | None
    price_raw: str | None
    confidence: float | None
    confidence_level: ConfidenceLevel | None
    review_status: ReviewStatus
    source_text: str | None


class ExtractedItemsListOut(BaseModel):
    items: list[ExtractedItemOut]
    page: int
    page_size: int
    total: int


class ReviewItemIn(BaseModel):
    decision: ReviewDecisionType
    notes: str | None = None
    field: str | None = None
    previous_value: str | None = None
    corrected_value: str | None = None
    reviewed_by_user_id: int | None = None
    # Preenchidos quando o revisor escolhe "Não está na lista — cadastrar
    # novo acabamento" (docs/04, seção 4, capacidade 5). Aplicável apenas
    # quando field == "finish_raw".
    new_finish_name: str | None = None
    new_finish_group: FinishGroup | None = None


class ReviewDecisionOut(BaseModel):
    id: int
    decision: ReviewDecisionType
    field_corrected: str | None
    previous_value: str | None
    corrected_value: str | None
    reviewed_by: UserSummary | None
    reviewed_at: str


class ReviewItemOut(BaseModel):
    id: int
    review_status: ReviewStatus
    decision: ReviewDecisionOut


# ---------------------------------------------------------------------------
# Correção em lote (docs/04, seção 4 — fluxo de correção em lote)
# ---------------------------------------------------------------------------

BatchCorrectionScope = Literal["page", "page_profile", "import"]


class BatchCorrectionCandidate(BaseModel):
    id: int
    page_number: int
    confidence_level: ConfidenceLevel | None
    previous_value: str | None
    corrected_value: str


class BatchCorrectionPreviewOut(BaseModel):
    field: str
    previous_value: str | None
    corrected_value: str
    scope: BatchCorrectionScope
    eligible_count: int
    already_decided_count: int
    already_decided_item_ids: list[int]
    candidates: list[BatchCorrectionCandidate]


class BatchCorrectionApplyIn(BaseModel):
    field: str
    scope: BatchCorrectionScope
    notes: str | None = None


class BatchCorrectionApplyOut(BaseModel):
    field: str
    previous_value: str | None
    corrected_value: str
    scope: BatchCorrectionScope
    applied_count: int
    applied_item_ids: list[int]
    skipped_item_ids: list[int]


# ---------------------------------------------------------------------------
# Aprovação/rejeição em lote (docs/04, seção 3 — barra de ações em lote)
# ---------------------------------------------------------------------------

BatchReviewDecision = Literal["aprovado", "rejeitado"]


class BatchReviewIn(BaseModel):
    item_ids: list[int]
    decision: BatchReviewDecision
    notes: str | None = None


class BatchReviewResultItem(BaseModel):
    item_id: int
    success: bool
    error_code: str | None = None
    error_message: str | None = None


class BatchReviewOut(BaseModel):
    decision: BatchReviewDecision
    requested_count: int
    succeeded_count: int
    failed_count: int
    results: list[BatchReviewResultItem]


# ---------------------------------------------------------------------------
# Importação via contrato JSON (docs/10; docs/07, Fase 13)
# ---------------------------------------------------------------------------

ImportJsonReviewStatus = Literal["aprovado", "pendente"]


class ImportJsonSourceIn(BaseModel):
    description: str | None = None
    generated_by: str | None = None
    generated_at: str | None = None


class ImportJsonItemIn(BaseModel):
    ref: str | None = None
    family: str
    product_context: str | None = None
    component_type: str
    description: str | None = None
    dimension: str
    finish: str
    finish_group: FinishGroup | None = None
    sku: str | None = None
    price: float = Field(ge=0)
    currency: str = "BRL"
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    notes: str | None = None


class ImportJsonIn(BaseModel):
    contract_version: Literal["1.0"]
    source: ImportJsonSourceIn | None = None
    items: list[ImportJsonItemIn] = Field(min_length=1)


class ImportJsonItemResult(BaseModel):
    ref: str | None
    extracted_item_id: int
    review_status: ImportJsonReviewStatus
    reasons: list[str] | None = None


class ImportJsonOut(BaseModel):
    imported_file_id: int
    items_total: int
    items_published: int
    items_pending_review: int
    warnings_count: int
    items: list[ImportJsonItemResult]
