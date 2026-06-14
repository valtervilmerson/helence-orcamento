from fastapi import APIRouter

from app.admin.router import router as admin_router
from app.auth.router import router as auth_router
from app.catalog.router import router as catalog_router
from app.imports.router import extracted_items_router
from app.imports.router import router as imports_router
from app.quotes.router import customers_router
from app.quotes.router import router as quotes_router

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
def get_health() -> dict[str, str]:
    return {"status": "ok"}


router.include_router(auth_router)
router.include_router(catalog_router)
router.include_router(quotes_router)
router.include_router(customers_router)
router.include_router(imports_router)
router.include_router(extracted_items_router)
router.include_router(admin_router)
