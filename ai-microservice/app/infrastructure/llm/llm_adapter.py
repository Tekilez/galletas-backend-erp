"""Infrastructure LLM adapter - implementa LlmPort."""
import random
import re
from app.infrastructure.config.settings import get_settings
from app.domain.ports.llm_port import LlmPort

settings = get_settings()

SYSTEM_PROMPT = """Eres un analista senior de retail y control de inventario (Kardex) para una tienda de galletas en Perú (Galletar Store).
Tu tarea: con los datos del Kardex que te dan (más vendidos, menos vendidos, stock crítico), genera UN SOLO PÁRRAFO (4-6 oraciones) en español neutro, directo y accionable.

Reglas:
- No uses bullet points ni saltos de línea. Un párrafo continuo.
- Menciona 1-2 productos top y 1 producto de baja rotación con nombre exacto.
- Recomienda 2 estrategias concretas: ej. bundle, descuento, reposición, liquidación, exhibición, campaña en redes.
- Considera margen y estacionalidad (campaña navideña, fin de semana, etc. si aparece en notas).
- Tono: profesional, optimista, orientado a dueña de tienda.
- No inventes cifras fuera de las provistas. No saludes, ve al grano.
- Cierra con una acción prioritaria para la próxima semana.
"""

def _build_user_prompt(data) -> str:
    def fmt(items):
        if not items:
            return " (sin datos)"
        lines = []
        for it in items[:5]:
            lines.append(f"- {it.producto_nombre} ({it.categoria or 's/categoria'}, SKU {it.variante_sku or 'N/A'}): vendidos {it.total_vendido}, stock {it.stock_actual}, PV S/{it.precio_venta}")
        return "\n".join(lines)
    return f"""Periodo: {data.periodo}

Productos MÁS vendidos:
{fmt(data.productos_mas_vendidos)}

Productos MENOS vendidos:
{fmt(data.productos_menos_vendidos)}

Stock crítico (≤ stock mínimo):
{fmt(data.stock_critico or [])}

Notas adicionales: {data.notas_adicionales or 'Ninguna'}

Genera el párrafo ahora.
"""

async def _llm_mock(prompt: str) -> str:
    templates = [
        "El Kardex muestra tracción clara en {top} con alta rotación, por lo que conviene reponer stock esta semana y negociar mejor precio de costo por volumen con el proveedor; en contraste, {low} presenta baja salida y riesgo de convertirse en stock muerto, así que recomiendo liquidarlo con un bundle ({low} + accesorio) o descuento del 15% y reubicarlo a zona visible en tienda y portada de Instagram. Para el stock crítico, prioriza la reposición de {top} antes de quiebre y evita sobrestockear {low}. Como acción prioritaria, lanza una campaña de 7 días '2x1 en {low} por compra de {top}' para equilibrar flujo de caja y liberar almacén.",
        "Durante el periodo, {top} lidera ventas y valida el margen actual, por lo que sugiere mantener precio y aumentar exhibición en maniquí y stories; mientras {low} arrastra rotación lenta, ideal para activar una estrategia de liquidación cruzada (ej. {low} con 20% off si llevan {top}) y revisar si el precio de costo permite ajustar margen sin perder rentabilidad. El stock crítico de {top} debe reponerse de inmediato para no perder ventas por quiebre. Acción prioritaria: reabastecer {top} y mover {low} a combo promocional esta semana.",
    ]
    top = "Galleta Chocochips Clasica"
    low = "Galleta Avena Integral"
    m = re.findall(r"- ([^\(]+) \(", prompt)
    if len(m) >= 2:
        top, low = m[0].strip(), m[-1].strip()
    elif len(m) == 1:
        top = m[0].strip()
    tpl = random.choice(templates)
    return tpl.format(top=top, low=low)

async def _llm_google(prompt: str) -> str:
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.google_api_key)
        model = genai.GenerativeModel(
            model_name=settings.google_model,
            system_instruction=SYSTEM_PROMPT,
        )
        resp = await model.generate_content_async(prompt)
        if resp is None or not hasattr(resp, "text"):
            resp = model.generate_content(prompt)
        return resp.text.strip()
    except ImportError:
        return await _llm_mock(prompt)
    except Exception as e:
        print(f"[LLM Google error] {e}")
        return await _llm_mock(prompt)

async def _llm_ollama(prompt: str) -> str:
    try:
        import httpx
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{settings.ollama_base_url}/api/generate", json={
                "model": settings.ollama_model,
                "prompt": SYSTEM_PROMPT + "\n\nUSUARIO:\n" + prompt,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 350}
            })
            r.raise_for_status()
            data = r.json()
            return data.get("response", "").strip() or await _llm_mock(prompt)
    except Exception as e:
        print(f"[LLM Ollama error] {e}")
        return await _llm_mock(prompt)

class LlmAdapter(LlmPort):
    async def generate(self, payload) -> tuple[str, str, str]:
        provider = settings.llm_provider.lower()
        user_prompt = _build_user_prompt(payload)
        if provider == "google" and settings.google_api_key:
            text = await _llm_google(user_prompt)
            return text, "google", settings.google_model
        elif provider == "ollama":
            text = await _llm_ollama(user_prompt)
            return text, "ollama", settings.ollama_model
        else:
            text = await _llm_mock(user_prompt)
            return text, "mock", "template-v1"

# Funciones de compatibilidad (hexagonal pero re-exportadas en services)
llm_adapter = LlmAdapter()

def build_user_prompt(data):
    return _build_user_prompt(data)

async def generate_insights(data) -> tuple[str, str, str]:
    return await llm_adapter.generate(data)

# expose mock for tests
_llm_mock = _llm_mock
_build_user_prompt = _build_user_prompt
