"""Adapter secundario: Supabase -> NotaVentaRepositoryPort (con transacciones kardex)."""
import random
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import HTTPException
from app.domain.ports.nota_venta_repository import NotaVentaRepositoryPort
from app.infrastructure.persistence.supabase_client import require_supabase

def _gen_codigo() -> str:
    now = datetime.now()
    suffix = "".join(random.choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=4))
    return f"NV-{now.strftime('%Y%m%d')}-{suffix}"

class SupabaseNotaRepository(NotaVentaRepositoryPort):
    def list(self, cliente_id: Optional[str], vendedor_id: Optional[str], limit: int, offset: int) -> List[Dict[str, Any]]:
        sb = require_supabase()
        q = sb.table("notas_venta").select("*").order("created_at", desc=True).range(offset, offset + limit - 1)
        if cliente_id:
            q = q.eq("cliente_id", cliente_id)
        if vendedor_id:
            q = q.eq("vendedor_id", vendedor_id)
        try:
            res = q.execute()
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        return res.data

    def get_by_id(self, nota_id: str) -> Optional[Dict[str, Any]]:
        sb = require_supabase()
        try:
            res = sb.table("notas_venta").select("*").eq("id", nota_id).single().execute()
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Nota {nota_id} no encontrada: {e}")
        if not res.data:
            raise HTTPException(status_code=404, detail="Nota no encontrada")
        return res.data

    def get_with_detalle(self, nota_id: str) -> Optional[Dict[str, Any]]:
        sb = require_supabase()
        try:
            nota = sb.table("notas_venta").select("*").eq("id", nota_id).single().execute()
            if not nota.data:
                raise HTTPException(status_code=404, detail="Nota no encontrada")
            detalle = sb.table("detalle_nota").select("*").eq("nota_id", nota_id).execute()
            # enriquecer con variante info
            data = nota.data
            data["detalles"] = detalle.data
            return data
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    def create_nota(self, cliente_id: Optional[str], vendedor_id: Optional[str], codigo_barras: str, total: float, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        sb = require_supabase()
        if not codigo_barras:
            codigo_barras = _gen_codigo()
        # Validar stock antes y preparar transacciones
        for it in items:
            var_id = it["variante_id"]
            cant = int(it["cantidad"])
            try:
                var = sb.table("variantes").select("stock_actual, precio_venta").eq("id", var_id).single().execute()
                if not var.data:
                    raise HTTPException(status_code=404, detail=f"Variante {var_id} no existe")
                if var.data["stock_actual"] < cant:
                    raise HTTPException(status_code=409, detail=f"Stock insuficiente variante {var_id}: disponible {var.data['stock_actual']}, solicitado {cant}")
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        # Crear cabecera
        try:
            nota_res = sb.table("notas_venta").insert({
                "cliente_id": cliente_id,
                "vendedor_id": vendedor_id,
                "codigo_barras": codigo_barras,
                "total": total
            }).select().single().execute()
            nota = nota_res.data
            nota_id = nota["id"]
        except Exception as e:
            msg = str(e)
            if "duplicate" in msg.lower() or "23505" in msg:
                # reintentar con nuevo codigo
                return self.create_nota(cliente_id, vendedor_id, _gen_codigo(), total, items)
            raise HTTPException(status_code=400, detail=msg)

        # Crear detalles
        try:
            detalle_rows = []
            for it in items:
                detalle_rows.append({
                    "nota_id": nota_id,
                    "variante_id": it["variante_id"],
                    "cantidad": it["cantidad"],
                    "precio_unitario": it["precio_unitario"]
                })
            sb.table("detalle_nota").insert(detalle_rows).execute()
        except Exception as e:
            # rollback cabecera si falla detalle
            try:
                sb.table("notas_venta").delete().eq("id", nota_id).execute()
            except Exception:
                pass
            raise HTTPException(status_code=400, detail=str(e))

        # Disparar transacciones salida por cada item (descuenta stock via trigger)
        for it in items:
            var_id = it["variante_id"]
            cant = int(it["cantidad"])
            precio = float(it["precio_unitario"])
            # obtener stock actual fresco para stock_anterior
            try:
                var = sb.table("variantes").select("stock_actual").eq("id", var_id).single().execute()
                stock_ant = var.data["stock_actual"]
                stock_nuevo = stock_ant - cant
                sb.table("transacciones").insert({
                    "variante_id": var_id,
                    "tipo": "salida",
                    "cantidad": cant,
                    "precio_unitario": precio,
                    "stock_anterior": stock_ant,
                    "stock_nuevo": stock_nuevo,
                    "motivo": "venta nota",
                    "referencia": codigo_barras
                }).execute()
            except Exception as e:
                # log pero no revertir nota (kardex inconsistente si falla, pero se reporta)
                raise HTTPException(status_code=500, detail=f"Nota creada pero fallo kardex variante {var_id}: {e}")

        # Retornar con detalle
        return self.get_with_detalle(nota_id)

    def delete(self, nota_id: str) -> None:
        sb = require_supabase()
        try:
            sb.table("notas_venta").delete().eq("id", nota_id).execute()
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
