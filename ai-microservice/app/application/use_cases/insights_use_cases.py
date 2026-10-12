"""Application - Caso de uso Insights."""
from datetime import datetime, timezone
from app.domain.ports.llm_port import LlmPort
from app.interfaces.api.schemas import InventoryInsightsRequest, InventoryInsightsResponse

class InsightsUseCases:
    def __init__(self, llm_port: LlmPort):
        self.llm = llm_port

    async def generate(self, payload: InventoryInsightsRequest) -> InventoryInsightsResponse:
        analisis, provider, model = await self.llm.generate(payload)
        analisis = " ".join(analisis.strip().split())
        return InventoryInsightsResponse(
            analisis=analisis,
            llm_provider=provider,
            model=model,
            generated_at=datetime.now(timezone.utc),
        )

    async def generate_mock(self, payload: InventoryInsightsRequest) -> InventoryInsightsResponse:
        from app.infrastructure.llm.llm_adapter import _llm_mock, _build_user_prompt
        prompt = _build_user_prompt(payload)
        text = await _llm_mock(prompt)
        return InventoryInsightsResponse(
            analisis=" ".join(text.split()),
            llm_provider="mock",
            model="template-v1",
            generated_at=datetime.now(timezone.utc),
        )
