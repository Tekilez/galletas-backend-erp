"""Adapter primario: Control de Asistencia y Turnos (Entrada/Salida de Vendedores)."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.infrastructure.auth.jwt_handler import get_current_vendedor
from app.infrastructure.persistence.supabase_client import require_supabase

router = APIRouter(prefix="/api/v1/asistencia", tags=["Asistencia"])

class EntradaRequest(BaseModel):
    observaciones: Optional[str] = None

class SalidaRequest(BaseModel):
    asistencia_id: Optional[str] = None
    observaciones: Optional[str] = None

@router.post("/marcar-entrada", summary="Registra hora de entrada del vendedor")
def marcar_entrada(payload: Optional[EntradaRequest] = None, vendedor=Depends(get_current_vendedor)):
    sb = require_supabase()
    try:
        v_id = vendedor.get("id") if vendedor.get("id") != "remote" else None
        usuario = vendedor.get("usuario", "vendedor")
        nombre = vendedor.get("nombre", usuario)

        # Verificar si ya tiene un turno activo abierto hoy
        now_dt = datetime.now(timezone.utc)
        today_str = now_dt.strftime("%Y-%m-%d")

        query = sb.table("control_asistencia").select("*").eq("usuario", usuario).eq("estado", "activo").order("entrada_at", desc=True).limit(1)
        res = query.execute()

        if res.data and len(res.data) > 0:
            active = res.data[0]
            # Si el turno es de hoy, devolvemos el activo
            if active.get("fecha") == today_str:
                return {
                    "success": True,
                    "message": "Ya tienes un turno activo iniciado",
                    "data": active,
                    "is_new": False
                }

        # Crear nuevo registro de entrada
        insert_data = {
            "vendedor_id": v_id,
            "usuario": usuario,
            "nombre": nombre,
            "fecha": today_str,
            "entrada_at": now_dt.isoformat(),
            "estado": "activo",
            "observaciones": payload.observaciones if payload else None,
        }
        ins_res = sb.table("control_asistencia").insert(insert_data).execute()
        return {
            "success": True,
            "message": "Hora de entrada registrada exitosamente",
            "data": ins_res.data[0] if ins_res.data else insert_data,
            "is_new": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al registrar entrada: {str(e)}")

@router.post("/marcar-salida", summary="Registra hora de salida y calcula jornada")
def marcar_salida(payload: Optional[SalidaRequest] = None, vendedor=Depends(get_current_vendedor)):
    sb = require_supabase()
    try:
        usuario = vendedor.get("usuario", "vendedor")
        now_dt = datetime.now(timezone.utc)

        # Buscar turno activo
        record = None
        if payload and payload.asistencia_id:
            res = sb.table("control_asistencia").select("*").eq("id", payload.asistencia_id).single().execute()
            record = res.data
        else:
            res = sb.table("control_asistencia").select("*").eq("usuario", usuario).eq("estado", "activo").order("entrada_at", desc=True).limit(1).execute()
            if res.data and len(res.data) > 0:
                record = res.data[0]

        if not record:
            # Si no hay turno abierto previo, creamos uno con entrada estimada o cerramos directo
            insert_data = {
                "vendedor_id": vendedor.get("id") if vendedor.get("id") != "remote" else None,
                "usuario": usuario,
                "nombre": vendedor.get("nombre", usuario),
                "fecha": now_dt.strftime("%Y-%m-%d"),
                "entrada_at": now_dt.isoformat(),
                "salida_at": now_dt.isoformat(),
                "minutos_trabajados": 0,
                "estado": "cerrado",
                "observaciones": (payload.observaciones or "") + " (Cierre sin entrada previa registrada)",
            }
            ins_res = sb.table("control_asistencia").insert(insert_data).execute()
            return {
                "success": True,
                "message": "Salida registrada",
                "data": ins_res.data[0] if ins_res.data else insert_data,
                "resumen": {"horas": 0, "minutos": 0, "total_minutos": 0}
            }

        # Calcular tiempo trabajado
        entrada_dt = datetime.fromisoformat(record["entrada_at"].replace("Z", "+00:00"))
        diff = now_dt - entrada_dt
        total_seconds = max(0, int(diff.total_seconds()))
        minutos_trabajados = total_seconds // 60
        horas = minutos_trabajados // 60
        mins_restantes = minutos_trabajados % 60

        update_data = {
            "salida_at": now_dt.isoformat(),
            "minutos_trabajados": minutos_trabajados,
            "estado": "cerrado",
            "updated_at": now_dt.isoformat(),
        }
        if payload and payload.observaciones:
            update_data["observaciones"] = payload.observaciones

        up_res = sb.table("control_asistencia").update(update_data).eq("id", record["id"]).execute()
        updated_record = up_res.data[0] if up_res.data else {**record, **update_data}

        return {
            "success": True,
            "message": "Hora de salida registrada exitosamente",
            "data": updated_record,
            "resumen": {
                "horas": horas,
                "minutos": mins_restantes,
                "total_minutos": minutos_trabajados,
                "entrada_at": record["entrada_at"],
                "salida_at": update_data["salida_at"],
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al registrar salida: {str(e)}")

@router.get("/actual", summary="Obtiene el turno activo actual del vendedor")
def get_turno_actual(vendedor=Depends(get_current_vendedor)):
    sb = require_supabase()
    try:
        usuario = vendedor.get("usuario", "vendedor")
        res = sb.table("control_asistencia").select("*").eq("usuario", usuario).eq("estado", "activo").order("entrada_at", desc=True).limit(1).execute()
        if res.data and len(res.data) > 0:
            return {"success": True, "data": res.data[0]}
        return {"success": True, "data": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/historial", summary="Historial de entradas y salidas")
def get_historial(fecha: Optional[str] = None, limit: int = 50, vendedor=Depends(get_current_vendedor)):
    sb = require_supabase()
    try:
        query = sb.table("control_asistencia").select("*")
        # Si no es admin, solo puede ver sus propios registros
        if vendedor.get("rol") != "admin":
            query = query.eq("usuario", vendedor.get("usuario"))
        if fecha:
            query = query.eq("fecha", fecha)
        res = query.order("entrada_at", desc=True).limit(limit).execute()
        return {"success": True, "data": res.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
