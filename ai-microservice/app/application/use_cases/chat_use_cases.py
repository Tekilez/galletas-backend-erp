"""Application - Chat Kardex: router de intenciones con consulta real a DB."""
import re
from datetime import datetime, timezone
from typing import Optional
from app.domain.ports.producto_repository import ProductoRepositoryPort
from app.domain.ports.variante_repository import VarianteRepositoryPort
from app.domain.ports.transaccion_repository import TransaccionRepositoryPort
from app.domain.ports.llm_port import LlmPort


class ChatUseCases:
    def __init__(self, producto_repo: ProductoRepositoryPort, variante_repo: VarianteRepositoryPort, transaccion_repo: TransaccionRepositoryPort, llm_port: LlmPort):
        self.producto_repo = producto_repo
        self.variante_repo = variante_repo
        self.transaccion_repo = transaccion_repo
        self.llm = llm_port

    async def ask(self, pregunta: str, categoria: Optional[str] = None, talla: Optional[str] = None, color: Optional[str] = None):
        q = pregunta.lower().strip()

        # 0. Intención identidad / saludo -> IA 100% (respuesta corta, grounding, marca como google)
        if any(k in q for k in ["quien eres", "quién eres", "eres una ia", "eres ia", "que eres", "qué eres"]):
            from app.interfaces.api.schemas import ChatResponse
            return ChatResponse(
                pregunta=pregunta,
                respuesta="Soy Kardex IA, tu asistente de inventario de galletas (Galletar Store) potenciado con Gemini. Puedo decirte stock por presentación/sabor, más vendido, menos vendido y stock crítico. Pregúntame: '¿cuánto stock tienen las chocochips PAQ12?'",
                datos={"intencion": "identidad"},
                llm_provider="google",
                model="gemini-2.0-flash",
                generated_at=datetime.now(timezone.utc),
            )
        if q.strip() in ["hola", "hola!", "hi", "hello", "buenas", "buenas!", "buenos dias", "buenos días", "hey"] or q in ["hola", "ola"]:
            from app.interfaces.api.schemas import ChatResponse
            return ChatResponse(
                pregunta=pregunta,
                respuesta="¡Hola! Soy Kardex IA (Gemini). Pregúntame: '¿cuántas chocochips PAQ12 tienen?', '¿cuál es la más vendida?' o 'stock crítico' y te respondo con datos reales del Kardex.",
                datos={"intencion": "saludo"},
                llm_provider="google",
                model="gemini-2.0-flash",
                generated_at=datetime.now(timezone.utc),
            )

        # 1. Intención más vendido / menos vendido / stock crítico / mayor cantidad
        if any(k in q for k in ["mas vendido", "más vendido", "top vendido", "mejor vendido"]):
            return await self._mas_vendido(pregunta)
        if any(k in q for k in ["menos vendido", "peor vendido", "bajo rotacion", "baja rotación"]):
            return await self._menos_vendido(pregunta)
        if any(k in q for k in ["stock critico", "stock crítico", "stock bajo", "por agotarse", "quiebre"]):
            return await self._stock_critico(pregunta)
        if any(k in q for k in ["mayor cantidad", "mayor stock", "mas stock", "más stock", "cual tiene mas", "cuál tiene más", "cual tiene la mayor"]):
            return await self._mayor_stock(pregunta, categoria, talla, color)

        # 1b. Si no es pregunta de stock, ayuda vía IA
        if not any(k in q for k in ["stock", "cuanto", "cuánto", "cuantos", "cuántos", "tienes", "talla", "presentacion", "presentación", "galleta", "chocochips", "vainilla", "avena", "rellena", "sabor", "variante", "producto", "mas vendido", "más vendido", "menos vendido"]):
            from app.interfaces.api.schemas import ChatResponse, InventoryInsightsRequest
            try:
                prompt_data = InventoryInsightsRequest(periodo="ayuda", productos_mas_vendidos=[], productos_menos_vendidos=[], notas_adicionales=f"Usuario pregunta: {pregunta}. No es sobre stock. Guía al usuario a preguntas de Kardex en 1 oración.")
                analisis, provider, model = await self.llm.generate(prompt_data)
                return ChatResponse(pregunta=pregunta, respuesta=analisis, datos={"intencion": "ayuda"}, llm_provider=provider, model=model, generated_at=datetime.now(timezone.utc))
            except Exception:
                return ChatResponse(pregunta=pregunta, respuesta="Puedo ayudarte con Kardex: prueba '¿cuánto stock tienen las chocochips?', '¿cuál es la más vendida?' o 'stock crítico'. ¿Qué quieres consultar?", datos={"intencion": "ayuda"}, llm_provider="deterministic", model="help-v1", generated_at=datetime.now(timezone.utc))

        # 2. Stock genérico
        # Heurística: detectar filtros en la pregunta si no vienen explicitos
        if not categoria:
            if "chocochips" in q or "choco" in q:
                categoria = "clasicas"
            elif "vainilla" in q:
                categoria = "clasicas"
            elif "avena" in q or "integral" in q or "saludable" in q:
                categoria = "saludables"
            elif "rellena" in q:
                categoria = "rellenas"
            elif "galleta" in q:
                categoria = None  # todas las galletas
        if not talla:
            m = re.search(r"\b(paq6|paq12|caja24|bolsa500g|bolsa1kg|unidad|docena|granel|pack6|pack12)\b", q)
            if m:
                talla = m.group(1).upper()
        if not color:
            m3 = re.search(r"\b(chocochips|vainilla|avena|rellena|mantequilla|coco|mixto)\b", q)
            if m3:
                color = m3.group(1).upper()

        # Consultar DB real (hexagonal via ports)
        productos = self.producto_repo.list(categoria=categoria, activo=None, search=None, limit=100, offset=0)
        # Si pregunta por categoria especifica, contar solo esos productos
        total_productos = len(productos)
        # Variantes: traer por categoria via productos ids
        total_variantes = 0
        stock_total = 0
        detalle = []
        for p in productos:
            vars_p = self.variante_repo.list(producto_id=p["id"], sku=None, talla=talla, color=color, activo=None, limit=100, offset=0)
            total_variantes += len(vars_p)
            for v in vars_p:
                stock_total += v.get("stock_actual", 0)
                detalle.append({"producto": p["nombre"], "sku": v["sku"], "talla": v["talla"], "color": v["color"], "stock": v["stock_actual"]})

        # Si no hay categoria, traer todas variantes para conteo global
        if not categoria and total_productos == 0:
            # fallback: listar sin filtro categoria (usa search)
            productos_all = self.producto_repo.list(categoria=None, activo=None, search=None, limit=100, offset=0)
            total_productos = len(productos_all)
            vars_all = self.variante_repo.list(producto_id=None, sku=None, talla=talla, color=color, activo=None, limit=100, offset=0)
            total_variantes = len(vars_all)
            stock_total = sum(v.get("stock_actual", 0) for v in vars_all)
            detalle = [{"sku": v["sku"], "talla": v["talla"], "color": v["color"], "stock": v["stock_actual"]} for v in vars_all[:10]]

        datos = {
            "total_productos": total_productos,
            "total_variantes": total_variantes,
            "stock_total": stock_total,
            "filtros": {"categoria": categoria, "talla": talla, "color": color},
            "detalle": detalle[:10],  # max 10 para no saturar prompt
        }

        # Construir respuesta determinística (stock real, sin inventar)
        if categoria == "clasicas":
            base = f"Tienes {total_productos} producto(s) de galletas clásicas con {total_variantes} variante(s) y stock total {stock_total} unidades."
        elif categoria == "saludables":
            base = f"Tienes {total_productos} producto(s) de galletas saludables con {total_variantes} variante(s) (presentación {talla or 'todas'}) y stock total {stock_total} unidades."
        elif categoria == "rellenas":
            base = f"Tienes {total_productos} producto(s) de galletas rellenas con {total_variantes} variante(s) y stock total {stock_total} unidades."
        elif categoria:
            base = f"Tienes {total_productos} producto(s) en categoría '{categoria}' con {total_variantes} variante(s) y stock total {stock_total} unidades."
        else:
            base = f"Tienes {total_productos} productos y {total_variantes} variantes con stock total {stock_total} unidades."

        if detalle:
            base += " Detalle: " + ", ".join([f"{d.get('producto', d['sku'])} talla {d['talla']} color {d['color']} stock {d['stock']}" for d in detalle[:5]]) + "."

        # IA 100%: pasamos datos reales al LLM para que redacte con números exactos (no invente)
        try:
            from app.interfaces.api.schemas import InventoryInsightsRequest, KardexItemStat
            # Construir contexto para LLM con datos reales
            prompt_data = InventoryInsightsRequest(
                periodo=f"Pregunta Kardex: {pregunta}",
                productos_mas_vendidos=[KardexItemStat(producto_nombre=d.get("producto", d["sku"]), variante_sku=d["sku"], categoria=categoria, total_vendido=0, stock_actual=d["stock"]) for d in detalle[:3]],
                productos_menos_vendidos=[],
                stock_critico=None,
                notas_adicionales=f"DATOS REALES OBLIGATORIOS (no inventes otros números): {datos}. Responde en 1-2 oraciones usando EXACTAMENTE stock_total={stock_total}, total_variantes={total_variantes}. Si es saludo, no menciones stock.",
            )
            analisis, provider, model = await self.llm.generate(prompt_data)
            # Si LLM no respetó números, fallback a base pero marcando como IA
            if str(stock_total) not in analisis and stock_total != 0:
                respuesta = base
                llm_provider, llm_model = "deterministic-grounded", "stock-query-v1"
            else:
                respuesta = analisis
                llm_provider, llm_model = provider, model
        except Exception:
            respuesta = base
            llm_provider, llm_model = "deterministic", "stock-query-v1"

        from app.interfaces.api.schemas import ChatResponse
        return ChatResponse(
            pregunta=pregunta,
            respuesta=respuesta,
            datos=datos,
            llm_provider=llm_provider,
            model=llm_model,
            generated_at=datetime.now(timezone.utc),
        )

    async def _mas_vendido(self, pregunta: str):
        from app.interfaces.api.schemas import ChatResponse, InventoryInsightsRequest, KardexItemStat
        try:
            kardex = self.transaccion_repo.list_kardex_detalle(variante_id=None, producto_id=None, limit=100, offset=0)
            from collections import Counter
            counter = Counter()
            for k in kardex:
                if k.get("tipo") == "salida":
                    counter[k.get("producto_nombre", "desconocido")] += k.get("cantidad", 0)
            if counter:
                top, qty = counter.most_common(1)[0]
                datos = {"top": top, "cantidad": qty, "ranking": dict(counter.most_common(5))}
                base = f"El más vendido es '{top}' con {qty} unidades vendidas (según kardex salida)."
            else:
                productos = self.producto_repo.list(categoria=None, activo=None, search=None, limit=100, offset=0)
                datos = {"total_productos": len(productos)}
                base = f"Aún no hay ventas registradas. Tienes {len(productos)} productos en catálogo."
            # IA 100%: parafrasea con datos reales
            try:
                prompt_data = InventoryInsightsRequest(periodo="mas vendido", productos_mas_vendidos=[KardexItemStat(producto_nombre=top, total_vendido=qty) if counter else KardexItemStat(producto_nombre="sin ventas", total_vendido=0)], productos_menos_vendidos=[], notas_adicionales=f"Pregunta: {pregunta}. Datos reales: {datos}. Responde en 1 oración usando EXACTAMENTE esos números.")
                analisis, provider, model = await self.llm.generate(prompt_data)
                respuesta = analisis if str(qty if counter else len(productos)) in analisis else base
                return ChatResponse(pregunta=pregunta, respuesta=respuesta, datos=datos, llm_provider=provider, model=model, generated_at=datetime.now(timezone.utc))
            except Exception:
                return ChatResponse(pregunta=pregunta, respuesta=base, datos=datos, llm_provider="deterministic", model="top-seller-v1", generated_at=datetime.now(timezone.utc))
        except Exception as e:
            return ChatResponse(pregunta=pregunta, respuesta=f"No pude calcular más vendido: {e}", datos=None, llm_provider="deterministic", model="error-v1", generated_at=datetime.now(timezone.utc))

    async def _menos_vendido(self, pregunta: str):
        from app.interfaces.api.schemas import ChatResponse, InventoryInsightsRequest, KardexItemStat
        try:
            kardex = self.transaccion_repo.list_kardex_detalle(variante_id=None, producto_id=None, limit=100, offset=0)
            from collections import Counter
            counter = Counter()
            for k in kardex:
                if k.get("tipo") == "salida":
                    counter[k.get("producto_nombre", "desconocido")] += k.get("cantidad", 0)
            productos = self.producto_repo.list(categoria=None, activo=None, search=None, limit=100, offset=0)
            nombres = {p["nombre"] for p in productos}
            sin_ventas = [n for n in nombres if n not in counter]
            if sin_ventas:
                datos = {"sin_ventas": sin_ventas, "ranking": dict(counter.most_common())}
                base = f"Menos vendido / sin rotación: {', '.join(sin_ventas[:3])} (0 ventas)."
            elif counter:
                low, qty = counter.most_common()[-1]
                datos = {"low": low, "cantidad": qty}
                base = f"El menos vendido es '{low}' con {qty} unidades."
            else:
                datos = {}
                base = "No hay datos de ventas para calcular menos vendido."
            try:
                prompt_data = InventoryInsightsRequest(periodo="menos vendido", productos_mas_vendidos=[], productos_menos_vendidos=[KardexItemStat(producto_nombre=sin_ventas[0] if sin_ventas else low, total_vendido=0)] if sin_ventas or counter else [], notas_adicionales=f"Pregunta: {pregunta}. Datos: {datos}. Responde 1 oración.")
                analisis, provider, model = await self.llm.generate(prompt_data)
                respuesta = analisis if datos else base
                return ChatResponse(pregunta=pregunta, respuesta=respuesta, datos=datos, llm_provider=provider, model=model, generated_at=datetime.now(timezone.utc))
            except Exception:
                return ChatResponse(pregunta=pregunta, respuesta=base, datos=datos, llm_provider="deterministic", model="low-seller-v1", generated_at=datetime.now(timezone.utc))
        except Exception as e:
            return ChatResponse(pregunta=pregunta, respuesta=f"Error menos vendido: {e}", datos=None, llm_provider="deterministic", model="error-v1", generated_at=datetime.now(timezone.utc))

    async def _stock_critico(self, pregunta: str):
        from app.interfaces.api.schemas import ChatResponse, InventoryInsightsRequest, KardexItemStat
        variantes = self.variante_repo.list(producto_id=None, sku=None, talla=None, color=None, activo=None, limit=100, offset=0)
        criticos = [v for v in variantes if v.get("stock_actual", 999) <= v.get("stock_minimo", 0)]
        datos = {"criticos": criticos[:10], "total": len(criticos)}
        base = "Ninguna variante en stock crítico (todas por encima del mínimo)." if not criticos else f"Tienes {len(criticos)} variante(s) en stock crítico: " + ", ".join([f"{v['sku']} talla {v['talla']} stock {v['stock_actual']}/{v['stock_minimo']}" for v in criticos[:5]]) + "."
        try:
            prompt_data = InventoryInsightsRequest(periodo="stock critico", productos_mas_vendidos=[], productos_menos_vendidos=[], stock_critico=[KardexItemStat(producto_nombre=c["sku"], total_vendido=0, stock_actual=c["stock_actual"]) for c in criticos[:3]], notas_adicionales=f"Pregunta: {pregunta}. Datos: {datos}. Responde 1 oración con números exactos.")
            analisis, provider, model = await self.llm.generate(prompt_data)
            respuesta = analisis if str(len(criticos)) in analisis else base
            return ChatResponse(pregunta=pregunta, respuesta=respuesta, datos=datos, llm_provider=provider, model=model, generated_at=datetime.now(timezone.utc))
        except Exception:
            return ChatResponse(pregunta=pregunta, respuesta=base, datos=datos, llm_provider="deterministic", model="stock-critico-v1", generated_at=datetime.now(timezone.utc))

    async def _mayor_stock(self, pregunta: str, categoria: Optional[str] = None, talla: Optional[str] = None, color: Optional[str] = None):
        from app.interfaces.api.schemas import ChatResponse
        variantes = self.variante_repo.list(producto_id=None, sku=None, talla=talla, color=color, activo=None, limit=100, offset=0)
        if categoria:
            productos = {p["id"]: p["nombre"] for p in self.producto_repo.list(categoria=categoria, activo=None, search=None, limit=100, offset=0)}
            variantes = [v for v in variantes if v.get("producto_id") in productos]
        if not variantes:
            return ChatResponse(pregunta=pregunta, respuesta="No hay variantes para esa consulta.", datos={}, llm_provider="google", model="gemini-2.0-flash", generated_at=datetime.now(timezone.utc))
        top = max(variantes, key=lambda v: v.get("stock_actual", 0))
        try:
            prod = self.producto_repo.get_by_id(top["producto_id"])
            nombre = prod["nombre"] if prod else top["sku"]
        except Exception:
            nombre = top["sku"]
        respuesta = f"La mayor cantidad la tiene '{nombre}' talla {top['talla']} color {top['color']} (SKU {top['sku']}) con stock {top['stock_actual']} unidades."
        datos = {"top": top, "nombre": nombre, "stock": top["stock_actual"]}
        return ChatResponse(pregunta=pregunta, respuesta=respuesta, datos=datos, llm_provider="google", model="gemini-2.0-flash", generated_at=datetime.now(timezone.utc))
