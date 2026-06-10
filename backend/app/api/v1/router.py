from fastapi import APIRouter

from app.admin.router import router as admin_router
from app.catalog.router import router as catalog_router

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
def get_health() -> dict[str, str]:
    return {"status": "ok"}


router.include_router(catalog_router)
router.include_router(admin_router)
