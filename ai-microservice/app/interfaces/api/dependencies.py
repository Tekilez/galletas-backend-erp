"""DI Container hexagonal - wiring de ports -> adapters -> use_cases."""
from functools import lru_cache
from app.infrastructure.persistence.supabase_producto_repository import SupabaseProductoRepository
from app.infrastructure.persistence.supabase_variante_repository import SupabaseVarianteRepository
from app.infrastructure.persistence.supabase_transaccion_repository import SupabaseTransaccionRepository
from app.infrastructure.ocr.ocr_adapter import OcrAdapter
from app.infrastructure.llm.llm_adapter import LlmAdapter
from app.application.use_cases.producto_use_cases import ProductoUseCases
from app.application.use_cases.variante_use_cases import VarianteUseCases
from app.application.use_cases.transaccion_use_cases import TransaccionUseCases
from app.application.use_cases.ocr_use_cases import OcrUseCases
from app.application.use_cases.insights_use_cases import InsightsUseCases
from app.application.use_cases.chat_use_cases import ChatUseCases
from app.application.use_cases.cliente_use_cases import ClienteUseCases
from app.application.use_cases.nota_use_cases import NotaUseCases

@lru_cache
def get_producto_use_cases() -> ProductoUseCases:
    return ProductoUseCases(SupabaseProductoRepository())

@lru_cache
def get_variante_use_cases() -> VarianteUseCases:
    return VarianteUseCases(SupabaseVarianteRepository())

@lru_cache
def get_transaccion_use_cases() -> TransaccionUseCases:
    return TransaccionUseCases(SupabaseTransaccionRepository())

@lru_cache
def get_ocr_use_cases() -> OcrUseCases:
    return OcrUseCases(OcrAdapter())

@lru_cache
def get_insights_use_cases() -> InsightsUseCases:
    return InsightsUseCases(LlmAdapter())

@lru_cache
def get_chat_use_cases() -> ChatUseCases:
    return ChatUseCases(SupabaseProductoRepository(), SupabaseVarianteRepository(), SupabaseTransaccionRepository(), LlmAdapter())

@lru_cache
def get_cliente_use_cases() -> ClienteUseCases:
    from app.infrastructure.persistence.supabase_cliente_repository import SupabaseClienteRepository
    return ClienteUseCases(SupabaseClienteRepository())

@lru_cache
def get_nota_use_cases() -> NotaUseCases:
    from app.infrastructure.persistence.supabase_nota_repository import SupabaseNotaRepository
    return NotaUseCases(SupabaseNotaRepository())
