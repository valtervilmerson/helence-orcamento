"""Regras de negócio do ciclo de vida básico de orçamentos (docs/06, 14.10-14.13).

Forma simplificada da Fase 3 (docs/07): cada `quote_item` tem exatamente um
`quote_item_component` — sem composição múltipla (isso é a Fase 9).
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from typing import Any

from app.quotes import export, pricing, repository
from app.settings import repository as settings_repository
from app.quotes.schemas import (
    CustomerSummary,
    QuoteItemComponentCreateIn,
    QuoteItemComponentOut,
    QuoteItemComponentSwapIn,
    QuoteItemComponentSwapOut,
    QuoteItemCreateIn,
    QuoteItemOut,
    QuoteItemPatchIn,
    QuoteOut,
    QuoteReviewChecklistItem,
    QuoteReviewChecklistOut,
    QuoteSummaryOut,
    QuoteSummaryBucket,
    QuoteSettingsPatchIn,
    QuoteTotalsOut,
    QuoteTotalWarning,
    UserSummary,
)
from app.shared.errors import (
    CampoObrigatorioAusenteError,
    ClienteNaoEncontradoError,
    ComponenteNaoEncontradoError,
    ComposicaoIncompletaError,
    DescontoInvalidoError,
    DescontoSemJustificativaError,
    DescritorIncompativelError,
    FormatoInvalidoError,
    ItemNaoEncontradoError,
    ItemSemPrecoError,
    OrcamentoNaoEncontradoError,
    OrcamentoVazioError,
    QuantidadeInvalidaError,
    RevisaoPendenteError,
    StatusInvalidoError,
    TotaisNaoCalculadosError,
    TransicaoInvalidaError,
    UltimoComponenteError,
    VariacaoIncompativelError,
    VariacaoNaoEncontradaError,
)

logger = logging.getLogger("app.domain.quotes")

ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "rascunho": {"enviado", "rejeitado", "expirado"},
    "enviado": {"aprovado", "rejeitado", "expirado"},
    "aprovado": {"expirado"},
    "rejeitado": set(),
    "expirado": set(),
}


# ---------------------------------------------------------------------------
# Orçamento — 14.10
# ---------------------------------------------------------------------------


def _row_to_quote_out(row: sqlite3.Row) -> QuoteOut:
    created_by = None
    if row["created_by_id"] is not None:
        created_by = UserSummary(id=row["created_by_id"], name=row["created_by_name"])

    return QuoteOut(
        id=row["id"],
        quote_number=row["quote_number"],
        status=row["status"],
        customer=CustomerSummary(id=row["customer_id"], name=row["customer_name"]),
        created_by=created_by,
        created_at=row["created_at"],
        valid_until=row["valid_until"],
        notes=row["notes"],
        source_quote_id=row["source_quote_id"],
        markup_percent=row["markup_percent"] or 0.0,
        markup_uses_global=bool(row["markup_uses_global"]),
        quote_discount_percent=row["quote_discount_percent"],
        quote_discount_amount=row["quote_discount_amount"],
        quote_discount_reason=row["quote_discount_reason"],
        installment_count=row["installment_count"] or 1,
        installment_interest_percent=row["installment_interest_percent"] or 0.0,
        entrada_amount=row["entrada_amount"] or 0.0,
        entrada_percent=row["entrada_percent"] or 0.0,
    )


def get_quote(connection: sqlite3.Connection, quote_id: int) -> QuoteOut:
    row = repository.get_quote_row(connection, quote_id)
    if row is None:
        raise OrcamentoNaoEncontradoError(details={"id": quote_id})
    return _row_to_quote_out(row)


def list_quotes(connection: sqlite3.Connection) -> list[QuoteOut]:
    return [_row_to_quote_out(row) for row in repository.list_quote_rows(connection)]


def get_summary(connection: sqlite3.Connection) -> QuoteSummaryOut:
    buckets = {status: QuoteSummaryBucket(count=0, total=0.0) for status in ("rascunho", "enviado", "aprovado", "rejeitado", "expirado")}
    expiring: list[int] = []
    pending: list[int] = []
    today = datetime.now().date()
    for quote in list_quotes(connection):
        totals = get_totals(connection, quote.id)
        bucket = buckets[quote.status]
        buckets[quote.status] = QuoteSummaryBucket(count=bucket.count + 1, total=round(bucket.total + totals.total, 2))
        if quote.status == "rascunho" and not get_review_checklist(connection, quote.id).ready:
            pending.append(quote.id)
        if quote.status == "enviado" and quote.valid_until:
            try:
                if 0 <= (datetime.fromisoformat(quote.valid_until).date() - today).days <= 7:
                    expiring.append(quote.id)
            except ValueError:
                pass
    return QuoteSummaryOut(por_status=buckets, expirando_7d=expiring, pendencias=pending)


def delete_quote(connection: sqlite3.Connection, quote_id: int) -> None:
    if repository.get_quote_row(connection, quote_id) is None:
        raise OrcamentoNaoEncontradoError(details={"id": quote_id})
    repository.delete_quote(connection, quote_id)


def list_customers(connection: sqlite3.Connection) -> list[CustomerSummary]:
    return [
        CustomerSummary(id=row["id"], name=row["name"])
        for row in repository.list_customers(connection)
    ]


def create_customer(
    connection: sqlite3.Connection,
    name: str,
    document: str | None,
    email: str | None,
    phone: str | None,
    address: str | None,
) -> CustomerSummary:
    row = repository.create_customer(connection, name, document, email, phone, address)
    return CustomerSummary(id=row["id"], name=row["name"])


def create_quote(
    connection: sqlite3.Connection,
    customer_id: int,
    valid_until: str | None,
    notes: str | None,
    markup_percent: float = 0.0,
    quote_discount_percent: float | None = None,
    quote_discount_amount: float | None = None,
    quote_discount_reason: str | None = None,
    installment_count: int = 1,
    installment_interest_percent: float = 0.0,
    entrada_amount: float = 0.0,
    entrada_percent: float = 0.0,
) -> QuoteOut:
    customer = repository.get_customer(connection, customer_id)
    if customer is None:
        raise ClienteNaoEncontradoError(details={"customer_id": customer_id})

    quote_number = repository.next_quote_number(connection)
    quote_id = repository.insert_quote(
        connection,
        quote_number=quote_number,
        customer_id=customer_id,
        valid_until=valid_until,
        notes=notes,
        markup_percent=markup_percent or 0.0,
        quote_discount_percent=quote_discount_percent,
        quote_discount_amount=quote_discount_amount,
        quote_discount_reason=quote_discount_reason,
        installment_count=installment_count,
        installment_interest_percent=installment_interest_percent,
        entrada_amount=entrada_amount,
        entrada_percent=entrada_percent,
    )
    return get_quote(connection, quote_id)


def update_quote_settings(
    connection: sqlite3.Connection, quote_id: int, payload: QuoteSettingsPatchIn
) -> QuoteOut:
    _require_draft_quote(connection, quote_id)

    data = payload.model_dump(exclude_unset=True)

    markup = data.get("markup_percent")
    if markup is not None and markup < 0:
        raise DescontoInvalidoError(details={"markup_percent": markup, "message": "markup_percent não pode ser negativo."})

    # Se estiver definindo override específico, desativa herança global automaticamente
    if "markup_percent" in data and data.get("markup_uses_global") is None:
        data["markup_uses_global"] = False

    entrada = data.get("entrada_amount")
    if entrada is not None and entrada < 0:
        raise DescontoInvalidoError(details={"entrada_amount": entrada, "message": "entrada_amount não pode ser negativo."})

    entrada_pct = data.get("entrada_percent")
    if entrada_pct is not None and not (0 <= entrada_pct <= 100):
        raise DescontoInvalidoError(details={"entrada_percent": entrada_pct, "message": "entrada_percent deve estar entre 0 e 100."})

    # Exclusividade: definir um modo zera o outro
    if "entrada_percent" in data and data.get("entrada_percent", 0) > 0:
        data["entrada_amount"] = 0.0
    if "entrada_amount" in data and data.get("entrada_amount", 0) > 0:
        data["entrada_percent"] = 0.0

    has_pct = "quote_discount_percent" in data and data["quote_discount_percent"] is not None
    has_amt = "quote_discount_amount" in data and data["quote_discount_amount"] is not None
    if has_pct and has_amt:
        raise DescontoInvalidoError(
            details={"message": "Informe quote_discount_percent OU quote_discount_amount, não ambos."}
        )
    if has_pct and not (0 <= data["quote_discount_percent"] <= 100):
        raise DescontoInvalidoError(details={"quote_discount_percent": data["quote_discount_percent"]})
    if has_amt and data["quote_discount_amount"] < 0:
        raise DescontoInvalidoError(details={"quote_discount_amount": data["quote_discount_amount"]})

    # Garante exclusividade: ao definir um modo, limpa o outro
    if has_pct:
        data["quote_discount_amount"] = None
    if has_amt:
        data["quote_discount_percent"] = None

    repository.update_quote_settings(connection, quote_id, data)
    return get_quote(connection, quote_id)


def duplicate_quote(connection: sqlite3.Connection, quote_id: int) -> QuoteOut:
    """RN-17: duplica a estrutura do orçamento, reprecificando contra o
    preço atual de cada item.

    Componentes que não existirem mais (ou não tiverem preço) atualmente
    não bloqueiam a duplicação — ficam de fora da linha e a pendência é
    registrada em `duplication_pendencias` para revisão.
    """
    source_row = repository.get_quote_row(connection, quote_id)
    if source_row is None:
        raise OrcamentoNaoEncontradoError(details={"id": quote_id})

    quote_number = repository.next_quote_number(connection)
    new_quote_id = repository.insert_quote(
        connection,
        quote_number=quote_number,
        customer_id=source_row["customer_id"],
        valid_until=None,
        notes=source_row["notes"],
        source_quote_id=quote_id,
        markup_percent=source_row["markup_percent"] or 0.0,
        markup_uses_global=bool(source_row["markup_uses_global"]),
        quote_discount_percent=source_row["quote_discount_percent"],
        quote_discount_amount=source_row["quote_discount_amount"],
        quote_discount_reason=source_row["quote_discount_reason"],
        installment_count=source_row["installment_count"] or 1,
        installment_interest_percent=source_row["installment_interest_percent"] or 0.0,
        entrada_amount=source_row["entrada_amount"] or 0.0,
        entrada_percent=source_row["entrada_percent"] or 0.0,
    )

    for item_row in repository.list_items_with_components(connection, quote_id):
        new_item_id = repository.insert_item(
            connection,
            quote_id=new_quote_id,
            product_id=item_row["product_id"],
            label=item_row["label"],
            quantity=item_row["quantity"],
            notes=item_row["notes"],
        )

        if (
            item_row["discount_percent"] is not None
            or item_row["discount_amount"] is not None
            or item_row["discount_reason"] is not None
        ):
            repository.update_item(
                connection,
                new_item_id,
                {
                    "discount_percent": item_row["discount_percent"],
                    "discount_amount": item_row["discount_amount"],
                    "discount_reason": item_row["discount_reason"],
                },
            )

        pendencias: list[str] = []
        for component_row in repository.get_item_components(connection, item_row["id"]):
            variant_id = component_row["component_variant_id"]
            try:
                price_row = _get_frozen_price_row(connection, variant_id)
            except (VariacaoNaoEncontradaError, ItemSemPrecoError):
                descriptor = repository.get_variant_descriptor(connection, variant_id)
                descricao = (
                    descriptor["descriptor"] if descriptor is not None else f"variação {variant_id}"
                )
                sku = component_row["sku"] or "sem SKU"
                pendencias.append(
                    f"Componente '{descricao}' (SKU {sku}) sem preço atual — revisar."
                )
                continue

            repository.insert_item_component(
                connection,
                quote_item_id=new_item_id,
                component_variant_id=variant_id,
                sku_id=price_row["sku_id"],
                frozen_unit_price=price_row["amount"],
                frozen_currency=price_row["currency"],
                price_source_id=price_row["price_id"],
            )

        if pendencias:
            repository.update_item(
                connection, new_item_id, {"duplication_pendencias": json.dumps(pendencias)}
            )

    return get_quote(connection, new_quote_id)


def _require_draft_quote(connection: sqlite3.Connection, quote_id: int) -> sqlite3.Row:
    row = repository.get_quote_row(connection, quote_id)
    if row is None:
        raise OrcamentoNaoEncontradoError(details={"id": quote_id})
    if row["status"] != "rascunho":
        raise StatusInvalidoError(details={"status": row["status"]})
    return row


def _get_effective_markup_percent(connection: sqlite3.Connection, quote_row: sqlite3.Row) -> float:
    if quote_row["markup_uses_global"]:
        return settings_repository.get_global_markup(connection)
    return quote_row["markup_percent"] or 0.0


def _get_markup_factor(connection: sqlite3.Connection, quote_row: sqlite3.Row) -> float:
    return 1.0 + _get_effective_markup_percent(connection, quote_row) / 100.0


def _compute_effective_entrada(base_total: float, quote_row: sqlite3.Row) -> float:
    """Retorna o valor de entrada efetivo: fixo (R$) ou calculado (%) — mutuamente exclusivos."""
    pct = float(quote_row["entrada_percent"] or 0.0)
    if pct > 0:
        return round(base_total * pct / 100, 2)
    return round(float(quote_row["entrada_amount"] or 0.0), 2)


def _compute_installments(total: float, quote_row: sqlite3.Row) -> dict[str, Any]:
    count = int(quote_row["installment_count"] or 1)
    interest_pct = float(quote_row["installment_interest_percent"] or 0.0)
    interest_amt = round(total * interest_pct / 100.0, 2)
    inst_total = round(total + interest_amt, 2)
    inst_value = round(inst_total / count, 2) if count > 1 else inst_total
    return {
        "installment_count": count,
        "installment_interest_percent": interest_pct,
        "installment_interest_amount": interest_amt,
        "installment_total": inst_total,
        "installment_value": inst_value,
    }


# ---------------------------------------------------------------------------
# Itens — 14.11/14.12 (um único componente por item)
# ---------------------------------------------------------------------------


def _component_row_to_out(row: sqlite3.Row) -> QuoteItemComponentOut:
    return QuoteItemComponentOut(
        id=row["id"],
        component_variant_id=row["component_variant_id"],
        component=row["component"],
        descriptor=row["descriptor"],
        description=row["description"],
        sku=row["sku"],
        frozen_unit_price=row["frozen_unit_price"],
        frozen_currency=row["frozen_currency"],
        frozen_at=row["frozen_at"],
    )


def _missing_required_components(connection: sqlite3.Connection, item_row: sqlite3.Row) -> list[str]:
    """RN-07: nomes dos tipos de componente obrigatórios da família do item
    que ainda não estão presentes na linha.

    Itens sem família derivável (nenhum componente aponta para um produto
    com `family_id`) não têm exigência conhecida — retorna lista vazia.
    """
    family_id = repository.get_item_family_id(connection, item_row["id"])
    if family_id is None:
        return []

    required = repository.get_family_required_components(connection, family_id)
    if not required:
        return []

    present_component_ids: set[int] = set()
    for variant_id in repository.get_item_component_variant_ids(connection, item_row["id"]):
        descriptor = repository.get_variant_descriptor(connection, variant_id)
        if descriptor is not None:
            present_component_ids.add(descriptor["component_id"])

    return [row["name"] for row in required if row["component_id"] not in present_component_ids]


def _pricing_pendencias(item_row: sqlite3.Row) -> list[str]:
    """RN-17: pendências de reprecificação registradas ao duplicar o orçamento."""
    raw = item_row["duplication_pendencias"]
    return json.loads(raw) if raw else []


def _build_item_out(
    connection: sqlite3.Connection,
    item_row: sqlite3.Row,
    markup_factor: float = 1.0,
) -> QuoteItemOut:
    component_rows = repository.get_item_components(connection, item_row["id"])
    components = [_component_row_to_out(row) for row in component_rows]

    subtotal = pricing.line_subtotal(
        dict(item_row),
        [dict(row) for row in component_rows],
        markup_factor=markup_factor,
    )

    return QuoteItemOut(
        id=item_row["id"],
        quote_id=item_row["quote_id"],
        label=item_row["label"],
        quantity=item_row["quantity"],
        discount_percent=item_row["discount_percent"],
        discount_amount=item_row["discount_amount"],
        discount_reason=item_row["discount_reason"],
        notes=item_row["notes"],
        composition_justification=item_row["composition_justification"],
        missing_required_components=_missing_required_components(connection, item_row),
        pricing_pendencias=_pricing_pendencias(item_row),
        components=components,
        line_subtotal=round(subtotal, 2),
    )


def _get_frozen_price_row(
    connection: sqlite3.Connection, component_variant_id: int
) -> sqlite3.Row:
    """Valida RN-12/13/15: variação existe e tem preço próprio cadastrado."""
    if not repository.variant_exists(connection, component_variant_id):
        raise VariacaoNaoEncontradaError(details={"component_variant_id": component_variant_id})

    price_row = repository.get_variant_price(connection, component_variant_id)
    if price_row is None:
        raise ItemSemPrecoError(details={"component_variant_id": component_variant_id})
    return price_row


def _check_rn04_compatibility(
    connection: sqlite3.Connection, new_variant_id: int, existing_variant_ids: list[int]
) -> None:
    """RN-04: descritores de componentes diferentes na mesma linha devem ser
    compatíveis, segundo as regras cadastradas em `component_compatibility_rules`.

    A ausência de regra para um par de tipos de componente significa "sem
    restrição conhecida ainda" — não bloqueia.
    """
    new_descriptor = repository.get_variant_descriptor(connection, new_variant_id)
    if new_descriptor is None or new_descriptor["descriptor"] is None:
        return

    for existing_variant_id in existing_variant_ids:
        existing_descriptor = repository.get_variant_descriptor(connection, existing_variant_id)
        if existing_descriptor is None or existing_descriptor["descriptor"] is None:
            continue
        if existing_descriptor["component_id"] == new_descriptor["component_id"]:
            continue

        rules = repository.get_compatibility_rules_for_pair(
            connection, new_descriptor["component_id"], existing_descriptor["component_id"]
        )
        if not rules:
            continue

        compatible = any(
            (
                rule["component_a_id"] == new_descriptor["component_id"]
                and rule["descriptor_a"] == new_descriptor["descriptor"]
                and rule["component_b_id"] == existing_descriptor["component_id"]
                and rule["descriptor_b"] == existing_descriptor["descriptor"]
            )
            or (
                rule["component_a_id"] == existing_descriptor["component_id"]
                and rule["descriptor_a"] == existing_descriptor["descriptor"]
                and rule["component_b_id"] == new_descriptor["component_id"]
                and rule["descriptor_b"] == new_descriptor["descriptor"]
            )
            for rule in rules
        )
        if not compatible:
            raise DescritorIncompativelError(
                details={
                    "component_variant_id": new_variant_id,
                    "descriptor": new_descriptor["descriptor"],
                    "conflicting_component_variant_id": existing_variant_id,
                    "conflicting_descriptor": existing_descriptor["descriptor"],
                }
            )


def _resolve_component_variant_ids(payload: QuoteItemCreateIn) -> list[int]:
    """Aceita a forma simplificada (`component_variant_id`, Fase 3) ou a
    composição completa (`components`, docs/06 §14.11) — exatamente uma."""
    if payload.components:
        return [c.component_variant_id for c in payload.components]
    if payload.component_variant_id is not None:
        return [payload.component_variant_id]
    raise CampoObrigatorioAusenteError(
        details={"message": "Informe component_variant_id ou components."}
    )


def add_item(
    connection: sqlite3.Connection, quote_id: int, payload: QuoteItemCreateIn
) -> QuoteItemOut:
    quote_row = _require_draft_quote(connection, quote_id)
    markup_factor = _get_markup_factor(connection, quote_row)

    component_variant_ids = _resolve_component_variant_ids(payload)

    # Validações primeiro (RN-12/13/15 + RN-04): a linha inteira é criada com
    # todos os componentes precificados, ou nada é criado.
    price_rows = [
        _get_frozen_price_row(connection, variant_id)
        for variant_id in component_variant_ids
    ]
    for index, variant_id in enumerate(component_variant_ids):
        _check_rn04_compatibility(connection, variant_id, component_variant_ids[:index])

    item_id = repository.insert_item(
        connection,
        quote_id=quote_id,
        product_id=payload.product_id,
        label=payload.label,
        quantity=payload.quantity,
        notes=payload.notes,
    )
    for variant_id, price_row in zip(component_variant_ids, price_rows, strict=True):
        repository.insert_item_component(
            connection,
            quote_item_id=item_id,
            component_variant_id=variant_id,
            sku_id=price_row["sku_id"],
            frozen_unit_price=price_row["amount"],
            frozen_currency=price_row["currency"],
            price_source_id=price_row["price_id"],
        )

    item_row = repository.get_item_row(connection, quote_id, item_id)
    return _build_item_out(connection, item_row, markup_factor)


def list_items(connection: sqlite3.Connection, quote_id: int) -> list[QuoteItemOut]:
    if not repository.quote_exists(connection, quote_id):
        raise OrcamentoNaoEncontradoError(details={"id": quote_id})
    quote_row = repository.get_quote_row(connection, quote_id)
    markup_factor = _get_markup_factor(connection, quote_row)
    item_rows = repository.list_items_with_components(connection, quote_id)
    return [_build_item_out(connection, row, markup_factor) for row in item_rows]


def get_item(connection: sqlite3.Connection, quote_id: int, item_id: int) -> QuoteItemOut:
    if not repository.quote_exists(connection, quote_id):
        raise OrcamentoNaoEncontradoError(details={"id": quote_id})
    quote_row = repository.get_quote_row(connection, quote_id)
    markup_factor = _get_markup_factor(connection, quote_row)
    item_row = repository.get_item_row(connection, quote_id, item_id)
    if item_row is None:
        raise ItemNaoEncontradoError(details={"id": item_id})
    return _build_item_out(connection, item_row, markup_factor)


def add_component(
    connection: sqlite3.Connection,
    quote_id: int,
    item_id: int,
    payload: QuoteItemComponentCreateIn,
) -> QuoteItemOut:
    """Adiciona um componente a uma linha existente, validando RN-04 (docs/05)."""
    quote_row = _require_draft_quote(connection, quote_id)
    markup_factor = _get_markup_factor(connection, quote_row)

    item_row = repository.get_item_row(connection, quote_id, item_id)
    if item_row is None:
        raise ItemNaoEncontradoError(details={"id": item_id})

    price_row = _get_frozen_price_row(connection, payload.component_variant_id)

    existing_variant_ids = repository.get_item_component_variant_ids(connection, item_id)
    _check_rn04_compatibility(connection, payload.component_variant_id, existing_variant_ids)

    repository.insert_item_component(
        connection,
        quote_item_id=item_id,
        component_variant_id=payload.component_variant_id,
        sku_id=price_row["sku_id"],
        frozen_unit_price=price_row["amount"],
        frozen_currency=price_row["currency"],
        price_source_id=price_row["price_id"],
    )

    item_row = repository.get_item_row(connection, quote_id, item_id)
    return _build_item_out(connection, item_row, markup_factor)


def update_item_component(
    connection: sqlite3.Connection,
    quote_id: int,
    item_id: int,
    component_id: int,
    payload: QuoteItemComponentSwapIn,
) -> QuoteItemComponentSwapOut:
    """Troca a variação/acabamento de um componente já incluído, com
    recongelamento explícito (RN-06/16, docs/06 §14.12)."""
    _require_draft_quote(connection, quote_id)

    item_row = repository.get_item_row(connection, quote_id, item_id)
    if item_row is None:
        raise ItemNaoEncontradoError(details={"id": item_id})

    component_row = repository.get_item_component_row(connection, component_id)
    if component_row is None or component_row["quote_item_id"] != item_id:
        raise ComponenteNaoEncontradoError(details={"id": component_id})

    new_descriptor = repository.get_variant_descriptor(connection, payload.component_variant_id)
    if new_descriptor is None:
        raise VariacaoNaoEncontradaError(
            details={"component_variant_id": payload.component_variant_id}
        )

    old_descriptor = repository.get_variant_descriptor(
        connection, component_row["component_variant_id"]
    )
    if old_descriptor is None or old_descriptor["component_id"] != new_descriptor["component_id"]:
        raise VariacaoIncompativelError(
            details={
                "component_variant_id": payload.component_variant_id,
                "expected_component_id": old_descriptor["component_id"] if old_descriptor else None,
                "actual_component_id": new_descriptor["component_id"],
            }
        )

    price_row = _get_frozen_price_row(connection, payload.component_variant_id)
    previous_price = component_row["frozen_unit_price"]

    repository.update_item_component(
        connection,
        component_id,
        component_variant_id=payload.component_variant_id,
        sku_id=price_row["sku_id"],
        frozen_unit_price=price_row["amount"],
        frozen_currency=price_row["currency"],
        price_source_id=price_row["price_id"],
    )

    updated = repository.get_item_component_detail(connection, component_id)
    return QuoteItemComponentSwapOut(
        id=updated["id"],
        component_variant_id=updated["component_variant_id"],
        sku=updated["sku"],
        previous_frozen_unit_price=previous_price,
        frozen_unit_price=updated["frozen_unit_price"],
        frozen_currency=updated["frozen_currency"],
        frozen_at=updated["frozen_at"],
        price_changed=updated["frozen_unit_price"] != previous_price,
    )


def remove_item(connection: sqlite3.Connection, quote_id: int, item_id: int) -> None:
    """Remove uma linha (item) inteira do orçamento, com todos os seus componentes."""
    _require_draft_quote(connection, quote_id)

    item_row = repository.get_item_row(connection, quote_id, item_id)
    if item_row is None:
        raise ItemNaoEncontradoError(details={"id": item_id})

    repository.delete_item(connection, item_id)


def remove_component(
    connection: sqlite3.Connection, quote_id: int, item_id: int, component_id: int
) -> QuoteItemOut:
    """Remove um componente de uma linha existente.

    Remover o último componente de uma linha é bloqueado (`ULTIMO_COMPONENTE_DA_LINHA`)
    — para isso, a linha inteira deve ser removida (`remove_item`).
    """
    quote_row = _require_draft_quote(connection, quote_id)
    markup_factor = _get_markup_factor(connection, quote_row)

    item_row = repository.get_item_row(connection, quote_id, item_id)
    if item_row is None:
        raise ItemNaoEncontradoError(details={"id": item_id})

    component_row = repository.get_item_component_row(connection, component_id)
    if component_row is None or component_row["quote_item_id"] != item_id:
        raise ComponenteNaoEncontradoError(details={"id": component_id})

    if repository.count_item_components(connection, item_id) <= 1:
        raise UltimoComponenteError(details={"item_id": item_id, "component_id": component_id})

    repository.delete_item_component(connection, component_id)

    item_row = repository.get_item_row(connection, quote_id, item_id)
    return _build_item_out(connection, item_row, markup_factor)


def update_item(
    connection: sqlite3.Connection, quote_id: int, item_id: int, payload: QuoteItemPatchIn
) -> QuoteItemOut:
    quote_row = _require_draft_quote(connection, quote_id)
    markup_factor = _get_markup_factor(connection, quote_row)

    item_row = repository.get_item_row(connection, quote_id, item_id)
    if item_row is None:
        raise ItemNaoEncontradoError(details={"id": item_id})

    data = payload.model_dump(exclude_unset=True)

    if "quantity" in data and data["quantity"] is not None and data["quantity"] <= 0:
        raise QuantidadeInvalidaError(details={"quantity": data["quantity"]})

    has_percent = data.get("discount_percent") is not None
    has_amount = data.get("discount_amount") is not None
    if has_percent and has_amount:
        raise DescontoInvalidoError(
            details={"message": "Informe discount_percent OU discount_amount, não ambos."}
        )
    if has_percent and not (0 <= data["discount_percent"] <= 100):
        raise DescontoInvalidoError(details={"discount_percent": data["discount_percent"]})
    if has_amount and data["discount_amount"] < 0:
        raise DescontoInvalidoError(details={"discount_amount": data["discount_amount"]})

    # Garante exclusividade ao salvar: zera o outro modo de desconto
    if has_percent:
        data["discount_amount"] = None
    if has_amount:
        data["discount_percent"] = None

    has_reason = data.get("discount_reason") or item_row["discount_reason"]
    if (has_percent or has_amount) and not has_reason:
        raise DescontoSemJustificativaError()

    repository.update_item(connection, item_id, data)

    item_row = repository.get_item_row(connection, quote_id, item_id)
    return _build_item_out(connection, item_row, markup_factor)


# ---------------------------------------------------------------------------
# Status — mudança de etapa do ciclo de vida
# ---------------------------------------------------------------------------


def _check_composition_completeness(connection: sqlite3.Connection, quote_id: int) -> None:
    """RN-07: bloqueia rascunho -> enviado se houver linha sem componente(s)
    obrigatório(s) e sem justificativa registrada."""
    incomplete_items = []
    for item_row in repository.list_items_with_components(connection, quote_id):
        if item_row["composition_justification"]:
            continue
        missing = _missing_required_components(connection, item_row)
        if missing:
            incomplete_items.append(
                {"item_id": item_row["id"], "label": item_row["label"], "missing": missing}
            )

    if incomplete_items:
        raise ComposicaoIncompletaError(details={"items": incomplete_items})


def _build_review_checklist(
    connection: sqlite3.Connection, quote_id: int
) -> list[QuoteReviewChecklistItem]:
    """RN-18: checklist explícito de revisão final, com cada pendência nomeada
    e acionável.

    Item 5 (reconhecimento de tabela não-vigente/mista, RN-15) depende de
    definição comercial ainda em aberto (docs/05, pergunta de validação 5/10)
    e de um campo de confirmação ainda não modelado — fica fora desta versão
    do checklist.
    """
    item_rows = repository.list_items_with_components(connection, quote_id)
    quote_row = repository.get_quote_row(connection, quote_id)

    # 1. RN-07 — toda linha tem os componentes obrigatórios (ou justificativa).
    composicao_pendencias = []
    for item_row in item_rows:
        if item_row["composition_justification"]:
            continue
        missing = _missing_required_components(connection, item_row)
        if missing:
            composicao_pendencias.append(
                f"Linha '{item_row['label']}' está sem: {', '.join(missing)}."
            )

    # 2. RN-12/13 — nenhum componente sem preço congelado (rede de segurança).
    preco_pendencias = []
    for item_row in item_rows:
        for component_row in repository.get_item_components(connection, item_row["id"]):
            if component_row["frozen_unit_price"] is None:
                preco_pendencias.append(
                    f"Linha '{item_row['label']}' tem componente sem preço congelado."
                )

    # 3. Cliente definido e ao menos um item.
    cliente_item_pendencias = []
    if quote_row["customer_id"] is None:
        cliente_item_pendencias.append("Orçamento sem cliente definido.")
    if not item_rows:
        cliente_item_pendencias.append("Orçamento não tem nenhuma linha.")

    # 4. RN-09 — descontos com justificativa registrada.
    desconto_pendencias = []
    for item_row in item_rows:
        has_discount = (
            item_row["discount_percent"] is not None or item_row["discount_amount"] is not None
        )
        if has_discount and not item_row["discount_reason"]:
            desconto_pendencias.append(
                f"Linha '{item_row['label']}' tem desconto sem justificativa registrada."
            )

    return [
        QuoteReviewChecklistItem(
            code="COMPOSICAO_COMPLETA",
            label="Todas as linhas têm os componentes obrigatórios (RN-07)",
            ok=not composicao_pendencias,
            pendencias=composicao_pendencias,
        ),
        QuoteReviewChecklistItem(
            code="COMPONENTES_COM_PRECO_E_SKU",
            label="Nenhum componente está sem preço (RN-12/13)",
            ok=not preco_pendencias,
            pendencias=preco_pendencias,
        ),
        QuoteReviewChecklistItem(
            code="CLIENTE_E_ITENS",
            label="Cliente definido e ao menos um item",
            ok=not cliente_item_pendencias,
            pendencias=cliente_item_pendencias,
        ),
        QuoteReviewChecklistItem(
            code="DESCONTOS_JUSTIFICADOS",
            label="Descontos têm justificativa registrada (RN-09)",
            ok=not desconto_pendencias,
            pendencias=desconto_pendencias,
        ),
    ]


def get_review_checklist(connection: sqlite3.Connection, quote_id: int) -> QuoteReviewChecklistOut:
    if not repository.quote_exists(connection, quote_id):
        raise OrcamentoNaoEncontradoError(details={"id": quote_id})

    checklist = _build_review_checklist(connection, quote_id)
    return QuoteReviewChecklistOut(
        quote_id=quote_id,
        ready=all(item.ok for item in checklist),
        items=checklist,
    )


def update_status(connection: sqlite3.Connection, quote_id: int, new_status: str) -> QuoteOut:
    current_status = repository.get_quote_status(connection, quote_id)
    if current_status is None:
        raise OrcamentoNaoEncontradoError(details={"id": quote_id})

    allowed = ALLOWED_STATUS_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise TransicaoInvalidaError(
            details={"from": current_status, "to": new_status, "allowed": sorted(allowed)}
        )

    if new_status == "enviado":
        _check_composition_completeness(connection, quote_id)

    repository.update_quote_status(connection, quote_id, new_status)
    logger.info(
        "Orçamento #%s: status %s -> %s", quote_id, current_status, new_status
    )
    return get_quote(connection, quote_id)


# ---------------------------------------------------------------------------
# Totais — 14.13
# ---------------------------------------------------------------------------


def _items_with_components(connection: sqlite3.Connection, quote_id: int) -> list[dict[str, Any]]:
    items = repository.list_items_with_components(connection, quote_id)
    return [
        {
            "item": dict(item_row),
            "components": [
                dict(row) for row in repository.get_item_components(connection, item_row["id"])
            ],
        }
        for item_row in items
    ]


def get_totals(connection: sqlite3.Connection, quote_id: int) -> QuoteTotalsOut:
    if not repository.quote_exists(connection, quote_id):
        raise OrcamentoNaoEncontradoError(details={"id": quote_id})

    quote_row = repository.get_quote_row(connection, quote_id)
    entries = _items_with_components(connection, quote_id)
    totals = pricing.compute_totals(
        entries,
        markup_percent=_get_effective_markup_percent(connection, quote_row),
        quote_discount_percent=quote_row["quote_discount_percent"],
        quote_discount_amount=quote_row["quote_discount_amount"],
    )

    inst = _compute_installments(totals["total"], quote_row)
    base_total = inst["installment_total"] if inst["installment_count"] > 1 else totals["total"]
    entrada_amount = _compute_effective_entrada(base_total, quote_row)
    valor_restante = round(base_total - entrada_amount, 2)
    return QuoteTotalsOut(
        quote_id=quote_id,
        is_snapshot=False,
        calculated_at=_now(),
        warnings=[QuoteTotalWarning(**w) for w in totals["warnings"]],
        entrada_amount=entrada_amount,
        valor_restante=valor_restante,
        **{k: v for k, v in totals.items() if k != "warnings"},
        **inst,
    )


def freeze_totals(connection: sqlite3.Connection, quote_id: int) -> QuoteTotalsOut:
    if not repository.quote_exists(connection, quote_id):
        raise OrcamentoNaoEncontradoError(details={"id": quote_id})

    entries = _items_with_components(connection, quote_id)
    if not entries:
        raise OrcamentoVazioError(details={"quote_id": quote_id})

    checklist = _build_review_checklist(connection, quote_id)
    pending = [item for item in checklist if not item.ok]
    if pending:
        raise RevisaoPendenteError(
            details={"checklist": [item.model_dump() for item in pending]}
        )

    quote_row = repository.get_quote_row(connection, quote_id)
    totals = pricing.compute_totals(
        entries,
        markup_percent=_get_effective_markup_percent(connection, quote_row),
        quote_discount_percent=quote_row["quote_discount_percent"],
        quote_discount_amount=quote_row["quote_discount_amount"],
    )

    inst = _compute_installments(totals["total"], quote_row)
    base_total = inst["installment_total"] if inst["installment_count"] > 1 else totals["total"]
    entrada_amount = _compute_effective_entrada(base_total, quote_row)
    valor_restante = round(base_total - entrada_amount, 2)
    row = repository.upsert_quote_totals(
        connection,
        quote_id=quote_id,
        subtotal=totals["subtotal"],
        item_discount_amount=totals["item_discount_amount"],
        quote_discount_amount=totals["quote_discount_amount"],
        discount_percent=totals["discount_percent"],
        discount_amount=totals["discount_amount"],
        tax_amount=totals["tax_amount"],
        freight_amount=totals["freight_amount"],
        total=totals["total"],
        installment_count=inst["installment_count"],
        installment_interest_percent=inst["installment_interest_percent"],
        installment_interest_amount=inst["installment_interest_amount"],
        installment_total=inst["installment_total"],
        installment_value=inst["installment_value"],
        currency=totals["currency"],
    )
    logger.info(
        "Orçamento #%s: totais congelados (total=%.2f %s)",
        quote_id,
        totals["total"],
        totals["currency"],
    )

    return QuoteTotalsOut(
        quote_id=quote_id,
        subtotal=row["subtotal"],
        item_discount_amount=row["item_discount_amount"] or 0.0,
        quote_discount_amount=row["quote_discount_amount"] or 0.0,
        discount_percent=row["discount_percent"],
        discount_amount=row["discount_amount"],
        tax_amount=row["tax_amount"],
        freight_amount=row["freight_amount"],
        total=row["total"],
        installment_count=row["installment_count"] or 1,
        installment_interest_percent=row["installment_interest_percent"] or 0.0,
        installment_interest_amount=row["installment_interest_amount"] or 0.0,
        installment_total=row["installment_total"] or 0.0,
        installment_value=row["installment_value"] or 0.0,
        entrada_amount=entrada_amount,
        valor_restante=valor_restante,
        currency=row["currency"],
        is_snapshot=True,
        calculated_at=row["calculated_at"],
        warnings=[QuoteTotalWarning(**w) for w in totals["warnings"]],
    )


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Exportação — 14.14
# ---------------------------------------------------------------------------


def export_quote(connection: sqlite3.Connection, quote_id: int, format: str) -> tuple[bytes, str]:
    """RN-11/16: exporta o snapshot congelado do orçamento em PDF.

    Retorna `(conteúdo, nome_do_arquivo)`. Exige que os totais já tenham
    sido congelados (`POST /totals/freeze`) — caso contrário, falha com
    `TOTAIS_NAO_CALCULADOS`.
    """
    if format != "pdf":
        raise FormatoInvalidoError(details={"format": format})

    quote_row = repository.get_quote_row(connection, quote_id)
    if quote_row is None:
        raise OrcamentoNaoEncontradoError(details={"id": quote_id})

    if repository.get_quote_totals_row(connection, quote_id) is None:
        raise TotaisNaoCalculadosError(details={"id": quote_id})

    pdf_bytes = export.generate_pdf(connection, quote_id)
    filename = f"{quote_row['quote_number']}.pdf"
    return pdf_bytes, filename
