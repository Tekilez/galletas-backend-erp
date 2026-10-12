"""Adapter secundario: Supabase -> DevolucionRepositoryPort."""
import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import HTTPException
from app.domain.ports.devolucion_repository import DevolucionRepositoryPort
from app.infrastructure.persistence.supabase_client import require_supabase, single_row

def _gen_codigo_dv() -> str:
    now = datetime.now()
    suffix = "".join(random.choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=4))
    return f"DV-{now.strftime('%Y%m%d')}-{suffix}"

def _safe_float(x, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except (TypeError, ValueError):
        return default

def _sanitize_devolucion_row(d: Dict[str, Any], vendedores_map: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Limpia UNA fila para que siempre conforme DevolucionResponse. Nunca lanza."""
    try:
        if not isinstance(d, dict):
            return None
        if not d.get("id") or not d.get("codigo") or not d.get("nota_codigo"):
            return None
        items = d.get("items")
        if not isinstance(items, list):
            items = []
        vnombre = d.get("vendedor_nombre")
        cb = d.get("created_by")
        if not vnombre and cb and cb in vendedores_map:
            vnombre = vendedores_map[cb].get("nombre")
        cli = d.get("cliente") if isinstance(d.get("cliente"), dict) else None
        return {
            "id": str(d["id"]),
            "codigo": str(d["codigo"]),
            "nota_codigo": str(d["nota_codigo"]),
            "cliente": cli,
            "motivo": d.get("motivo"),
            "items": items,
            "total_devuelto": _safe_float(d.get("total_devuelto"), 0.0),
            "created_by": str(cb) if cb else None,
            "vendedor_nombre": vnombre,
            "created_at": d.get("created_at"),
        }
    except Exception as e:
        print(f"[DEVOLUCIONES SANITIZE] fila omitida: {e}")
        return None

class SupabaseDevolucionRepository(DevolucionRepositoryPort):
    def list(self, nota_codigo: Optional[str], q: Optional[str], limit: int, offset: int) -> List[Dict[str, Any]]:
        sb = require_supabase()
        rows: List[Dict[str, Any]] = []
        if q:
            try:
                res = sb.table("devoluciones").select("*").ilike("codigo", f"%{q}%").order("created_at", desc=True).range(offset, offset+limit-1).execute()
                rows = res.data or []
            except Exception as e:
                print(f"[DEVOLUCIONES LIST] q fail: {e}")
                rows = []
            if nota_codigo:
                rows = [r for r in rows if r.get("nota_codigo") == nota_codigo]
        else:
            query = sb.table("devoluciones").select("*").order("created_at", desc=True).range(offset, offset+limit-1)
            if nota_codigo:
                query = query.eq("nota_codigo", nota_codigo)
            try:
                res = query.execute()
                rows = res.data or []
            except Exception as e:
                print(f"[DEVOLUCIONES LIST] query fail: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        # batch vendedor_nombre en 1 query (evita N+1)
        vendedores_map: Dict[str, Any] = {}
        try:
            cbids = list({str(r.get("created_by")) for r in rows if r.get("created_by")})
            if cbids:
                try:
                    vres = sb.table("vendedores").select("id,nombre").in_("id", cbids).execute()
                    vendedores_map = {v["id"]: v for v in (vres.data or []) if isinstance(v, dict) and v.get("id")}
                except Exception as e:
                    print(f"[DEVOLUCIONES LIST] batch vendedores fail: {e}")
        except Exception as e:
            print(f"[DEVOLUCIONES LIST] enrich fail: {e}")
        out = []
        for d in rows:
            s = _sanitize_devolucion_row(d, vendedores_map)
            if s is not None:
                out.append(s)
        return out

    def get_by_codigo(self, codigo: str) -> Optional[Dict[str, Any]]:
        sb = require_supabase()
        try:
            res = sb.table("devoluciones").select("*").eq("codigo", codigo).single().execute()
            if not res.data:
                raise HTTPException(status_code=404, detail="Devolución no encontrada")
            return res.data
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))

    def create(self, nota_codigo: str, items: List[Dict[str, Any]], motivo_general: Optional[str], created_by: Optional[str]) -> Dict[str, Any]:
        sb = require_supabase()
        # 1. validar nota existe o auto-crear encabezado para FK
        nota = None
        try:
            nota_res = sb.table("notas_venta").select("*").eq("codigo_barras", nota_codigo).single().execute()
            nota = nota_res.data
        except Exception:
            try:
                nota_res = sb.table("notas_venta").select("*").eq("id", nota_codigo).single().execute()
                nota = nota_res.data
            except Exception:
                pass

        if not nota:
            # Auto-crear cabecera de nota para asegurar integridad referencial
            try:
                ins_nota = sb.table("notas_venta").insert({
                    "codigo_barras": nota_codigo,
                    "total": 0,
                    "vendedor_id": created_by,
                    "created_by": created_by
                }).select().execute()
                nota = single_row(ins_nota)
            except Exception as e:
                print(f"[DEVOLUCION AUTO-NOTA] {e}")

        # 2. detalle original y ya devuelto
        detalle_map = {}
        if nota and nota.get("id"):
            try:
                det_res = sb.table("detalle_nota").select("*").eq("nota_id", nota["id"]).execute()
                detalle_map = {d["variante_id"]: d["cantidad"] for d in (det_res.data or []) if isinstance(d, dict)}
            except Exception:
                detalle_map = {}

        # ya devuelto por variante
        devuelto_map = {}
        try:
            devs = sb.table("devoluciones").select("items").eq("nota_codigo", nota_codigo).execute()
            for d in (devs.data or []):
                for it in (d.get("items") or []):
                    if isinstance(it, dict) and "variante_id" in it:
                        devuelto_map[it["variante_id"]] = devuelto_map.get(it["variante_id"], 0) + int(it.get("cantidad", 1))
        except Exception:
            devuelto_map = {}

        total_devuelto = 0
        for it in items:
            var_id = it.get("variante_id")
            cant = int(it.get("cantidad", 1))
            pv = 0.0
            pv_original = 0.0
            
            # Obtener precio original de la variante
            try:
                var = sb.table("variantes").select("precio_venta").eq("id", var_id).single().execute()
                pv_original = float(var.data["precio_venta"]) if var.data and var.data.get("precio_venta") is not None else 0.0
            except Exception:
                pv_original = 0.0

            if nota and nota.get("id"):
                try:
                    det = sb.table("detalle_nota").select("precio_unitario").eq("nota_id", nota["id"]).eq("variante_id", var_id).single().execute()
                    if det.data and det.data.get("precio_unitario") is not None:
                        pv = float(det.data["precio_unitario"])
                except Exception:
                    pass
            if pv == 0.0:
                pv = pv_original
            
            # Guardar el precio cobrado en el item para que el frontend pueda mostrarlo
            it["precio_unitario"] = round(pv, 2)
            it["precio_original"] = round(pv_original, 2)
            total_devuelto += pv * cant

        codigo = _gen_codigo_dv()
        cliente = (nota.get("cliente") if nota else None) or {}
        if not cliente and nota and nota.get("cliente_id"):
            try:
                cli = sb.table("clientes").select("*").eq("id", nota["cliente_id"]).single().execute()
                if cli.data:
                    cliente = {"nombre": cli.data["nombre"], "dni": cli.data.get("dni"), "telefono": cli.data.get("telefono")}
            except Exception:
                pass

        # snapshot vendedor_nombre
        vendedor_nombre = None
        vendedor_id = (nota.get("vendedor_id") or nota.get("created_by")) if nota else None
        if created_by:
            vendedor_id = created_by
        if vendedor_id:
            try:
                v = sb.table("vendedores").select("nombre").eq("id", vendedor_id).single().execute()
                vendedor_nombre = v.data["nombre"] if v.data else None
            except Exception:
                pass

        try:
            payload = {
                "codigo": codigo,
                "nota_codigo": nota_codigo,
                "cliente": cliente,
                "motivo": motivo_general,
                "items": items,
                "total_devuelto": round(total_devuelto, 2)
            }
            if vendedor_nombre:
                payload["vendedor_nombre"] = vendedor_nombre
            ins = sb.table("devoluciones").insert(payload).select().execute()
        except Exception as e:
            msg = str(e)
            if "duplicate" in msg.lower():
                return self.create(nota_codigo, items, motivo_general, created_by)
            # Reintento sin vendedor_nombre si columna no existe
            try:
                payload.pop("vendedor_nombre", None)
                ins = sb.table("devoluciones").insert(payload).select().execute()
            except Exception as e2:
                raise HTTPException(status_code=400, detail=str(e2))

        # 3. reponer stock: transacción tipo devolucion o entrada
        for it in items:
            var_id = it.get("variante_id")
            cant = int(it.get("cantidad", 1))
            try:
                var = sb.table("variantes").select("stock_actual").eq("id", var_id).single().execute()
                if var.data:
                    stock_ant = int(var.data.get("stock_actual") or 0)
                    stock_nuevo = stock_ant + cant
                    # Actualizar stock
                    try:
                        sb.table("variantes").update({"stock_actual": stock_nuevo}).eq("id", var_id).execute()
                    except Exception:
                        pass
                    # Registrar transaccion
                    try:
                        sb.table("transacciones").insert({
                            "variante_id": var_id,
                            "tipo": "entrada",
                            "cantidad": cant,
                            "precio_unitario": 0,
                            "stock_anterior": stock_ant,
                            "stock_nuevo": stock_nuevo,
                            "motivo": "Devolución " + (motivo_general or ""),
                            "referencia": codigo
                        }).execute()
                    except Exception:
                        pass
            except Exception as e:
                print(f"[REPOSICION STOCK VARIANTE {var_id}]: {e}")

        row = single_row(ins)
        if not row:
            # fallback select by codigo
            try:
                row = sb.table("devoluciones").select("*").eq("codigo", codigo).single().execute().data
            except Exception:
                pass
        if not row:
            raise HTTPException(status_code=400, detail="insert no retornó fila")
        return row

