"""Adapter primario: HTTP -> InsightsUseCases."""
from fastapi import APIRouter, Depends
from app.interfaces.api.schemas import InventoryInsightsRequest, InventoryInsightsResponse
from app.application.use_cases.insights_use_cases import InsightsUseCases
from app.interfaces.api.dependencies import get_insights_use_cases

router = APIRouter(prefix="/api/v1", tags=["Insights"])

@router.post(
    "/inventory-insights",
    response_model=InventoryInsightsResponse,
    summary="Chatbot / Insights de Kardex",
    description="Recibe estado del Kardex (más/menos vendidos) y devuelve análisis en 1 párrafo con recomendaciones."
)
async def inventory_insights(payload: InventoryInsightsRequest, uc: InsightsUseCases = Depends(get_insights_use_cases)):
    return await uc.generate(payload)

@router.post(
    "/inventory-insights/mock-demo",
    summary="Demo sin LLM (útil para tests)",
    include_in_schema=False,
)
async def inventory_insights_demo(payload: InventoryInsightsRequest, uc: InsightsUseCases = Depends(get_insights_use_cases)):
    return await uc.generate_mock(payload)
