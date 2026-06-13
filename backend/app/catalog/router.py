"""Endpoints REST do catálogo manual (docs/06, seções 14.8/14.9; docs/07, Fase 2)."""

import sqlite3

from fastapi import APIRouter, Depends, Query, status

from app.catalog import repository, service
from app.catalog.repository import SimpleRepository
from app.catalog.schemas import (
    CompatibilityRuleIn,
    CompatibilityRuleOut,
    CompatibilityRulePatch,
    ComponentVariantIn,
    ComponentVariantOut,
    ComponentVariantPatch,
    ComponentVariantSearchResult,
    DimensionIn,
    DimensionOut,
    DimensionPatch,
    FinishIn,
    FinishOut,
    FinishPatch,
    PriceTableSummary,
    ProductComponentIn,
    ProductComponentOut,
    ProductComponentPatch,
    ProductFamilyIn,
    ProductFamilyOut,
    ProductFamilyPatch,
    ProductIn,
    ProductOut,
    ProductPatch,
    PublishIn,
    PublishOut,
)
from app.db.connection import get_connection

router = APIRouter(tags=["catalog"])


def get_db() -> sqlite3.Connection:
    with get_connection() as connection:
        yield connection


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def _register_crud(
    *,
    path: str,
    repo: SimpleRepository,
    in_model: type,
    patch_model: type,
    out_model: type,
) -> None:
    @router.get(path, response_model=list[out_model], name=f"list_{path}")
    def list_all(connection: sqlite3.Connection = Depends(get_db)) -> list[dict]:
        return [_row_to_dict(row) for row in service.list_entities(connection, repo)]

    @router.post(
        path, response_model=out_model, status_code=status.HTTP_201_CREATED, name=f"create_{path}"
    )
    def create(payload: in_model, connection: sqlite3.Connection = Depends(get_db)) -> dict:  # type: ignore[valid-type]
        row = service.create_entity(connection, repo, payload.model_dump())
        return _row_to_dict(row)

    @router.get(f"{path}/{{id}}", response_model=out_model, name=f"get_{path}")
    def get_one(id: int, connection: sqlite3.Connection = Depends(get_db)) -> dict:
        return _row_to_dict(service.get_entity(connection, repo, id))

    @router.patch(f"{path}/{{id}}", response_model=out_model, name=f"update_{path}")
    def update(
        id: int,
        payload: patch_model,
        connection: sqlite3.Connection = Depends(get_db),  # type: ignore[valid-type]
    ) -> dict:
        data = payload.model_dump(exclude_unset=True)
        row = service.update_entity(connection, repo, id, data)
        return _row_to_dict(row)

    @router.delete(
        f"{path}/{{id}}",
        status_code=status.HTTP_204_NO_CONTENT,
        response_model=None,
        name=f"delete_{path}",
    )
    def delete(id: int, connection: sqlite3.Connection = Depends(get_db)) -> None:
        service.delete_entity(connection, repo, id)


_register_crud(
    path="/catalog/families",
    repo=repository.product_families,
    in_model=ProductFamilyIn,
    patch_model=ProductFamilyPatch,
    out_model=ProductFamilyOut,
)
_register_crud(
    path="/catalog/dimensions",
    repo=repository.dimensions,
    in_model=DimensionIn,
    patch_model=DimensionPatch,
    out_model=DimensionOut,
)
_register_crud(
    path="/catalog/finishes",
    repo=repository.finishes,
    in_model=FinishIn,
    patch_model=FinishPatch,
    out_model=FinishOut,
)
_register_crud(
    path="/catalog/component-types",
    repo=repository.product_components,
    in_model=ProductComponentIn,
    patch_model=ProductComponentPatch,
    out_model=ProductComponentOut,
)
_register_crud(
    path="/catalog/products",
    repo=repository.products,
    in_model=ProductIn,
    patch_model=ProductPatch,
    out_model=ProductOut,
)
_register_crud(
    path="/catalog/compatibility-rules",
    repo=repository.compatibility_rules,
    in_model=CompatibilityRuleIn,
    patch_model=CompatibilityRulePatch,
    out_model=CompatibilityRuleOut,
)


@router.get("/catalog/price-tables", response_model=list[PriceTableSummary])
def list_price_tables(connection: sqlite3.Connection = Depends(get_db)) -> list[dict]:
    return [_row_to_dict(row) for row in repository.list_price_tables(connection)]


@router.post("/price-tables/{id}/publish", response_model=PublishOut)
def publish_price_table(
    id: int, payload: PublishIn, connection: sqlite3.Connection = Depends(get_db)
) -> PublishOut:
    return service.publish_price_table(connection, id, payload)


# ---------------------------------------------------------------------------
# Variações vendáveis (component_variants + sku + price) — 14.8/14.9
# ---------------------------------------------------------------------------


@router.get("/components", response_model=ComponentVariantSearchResult)
def search_components(
    family: str | None = Query(default=None),
    product: str | None = Query(default=None),
    component: str | None = Query(default=None),
    dimension: str | None = Query(default=None),
    finish: str | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    connection: sqlite3.Connection = Depends(get_db),
) -> ComponentVariantSearchResult:
    return service.search_variants(
        connection,
        family=family,
        product=product,
        component=component,
        dimension=dimension,
        finish=finish,
        q=q,
        page=page,
        page_size=page_size,
    )


@router.post("/components", response_model=ComponentVariantOut, status_code=status.HTTP_201_CREATED)
def create_component(
    payload: ComponentVariantIn, connection: sqlite3.Connection = Depends(get_db)
) -> ComponentVariantOut:
    return service.create_variant(connection, payload)


@router.get("/components/{id}", response_model=ComponentVariantOut)
def get_component(id: int, connection: sqlite3.Connection = Depends(get_db)) -> ComponentVariantOut:
    return service.get_variant(connection, id)


@router.patch("/components/{id}", response_model=ComponentVariantOut)
def update_component(
    id: int, payload: ComponentVariantPatch, connection: sqlite3.Connection = Depends(get_db)
) -> ComponentVariantOut:
    return service.update_variant(connection, id, payload)


@router.delete("/components/{id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_component(id: int, connection: sqlite3.Connection = Depends(get_db)) -> None:
    service.delete_variant(connection, id)
