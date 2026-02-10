"""v1 роутер: собирает эндпоинты в один APIRouter."""

from fastapi import APIRouter

from ai_gateway.api.v1_chat import router as chat_router
from ai_gateway.api.v1_jobs import router as jobs_router
from ai_gateway.api.v1_models import router as models_router
from ai_gateway.api.v1_responses import router as responses_router

router = APIRouter()
router.include_router(responses_router)
router.include_router(chat_router)
router.include_router(models_router)
router.include_router(jobs_router)
