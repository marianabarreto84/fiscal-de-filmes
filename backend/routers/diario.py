from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from backend.database import get_db, dict_cursor

router = APIRouter()


class ReorderEntry(BaseModel):
    diario_id: str   # UUID
    dia_ordem: int


class ReorderRequest(BaseModel):
    entries: List[ReorderEntry]


@router.get("")
def get_diario(
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to:   Optional[str] = Query(None, description="YYYY-MM-DD"),
):
    today = date.today()
    if date_from is None:
        date_from = today.replace(day=1).isoformat()
    if date_to is None:
        date_to = today.isoformat()

    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("""
                SELECT
                    d.id              AS diario_id,
                    d.filme_id,
                    EXTRACT(YEAR  FROM d.assistido_em)::int AS ano_assistido,
                    EXTRACT(MONTH FROM d.assistido_em)::int AS mes_assistido,
                    EXTRACT(DAY   FROM d.assistido_em)::int AS dia_assistido,
                    d.hora_assistido,
                    d.minuto_assistido,
                    d.dia_ordem,
                    d.plataforma_id,
                    d.rewatch,
                    f.titulo          AS filme_titulo,
                    f.poster_path,
                    f.duracao_min,
                    p.nome            AS plataforma_nome,
                    p.logo_path       AS plataforma_logo
                FROM diario d
                JOIN filme f ON f.id = d.filme_id
                LEFT JOIN plataforma p ON p.id = d.plataforma_id
                WHERE d.assistido_em IS NOT NULL
                  AND d.assistido_em BETWEEN %s AND %s
                ORDER BY
                    d.assistido_em DESC,
                    CASE WHEN d.dia_ordem IS NOT NULL THEN 0 ELSE 1 END,
                    d.dia_ordem,
                    COALESCE(d.hora_assistido,    -1),
                    COALESCE(d.minuto_assistido, -1)
            """, (date_from, date_to))
            rows = cur.fetchall()

        days: dict = {}
        for r in rows:
            key = (r["ano_assistido"], r["mes_assistido"], r["dia_assistido"])
            if key not in days:
                days[key] = {
                    "ano":    r["ano_assistido"],
                    "mes":    r["mes_assistido"],
                    "dia":    r["dia_assistido"],
                    "filmes": [],
                }
            days[key]["filmes"].append({
                "diario_id":       r["diario_id"],
                "filme_id":        r["filme_id"],
                "filme_titulo":    r["filme_titulo"],
                "poster_path":     r["poster_path"],
                "duracao_min":     r["duracao_min"],
                "hora_assistido":  r["hora_assistido"],
                "minuto_assistido": r["minuto_assistido"],
                "dia_ordem":       r["dia_ordem"],
                "plataforma_id":   r["plataforma_id"],
                "plataforma_nome": r["plataforma_nome"],
                "plataforma_logo": r["plataforma_logo"],
                "rewatch":         r["rewatch"],
            })

        return list(days.values())
    finally:
        conn.close()


@router.patch("/reorder")
def reorder_day(body: ReorderRequest):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            for entry in body.entries:
                cur.execute(
                    "UPDATE diario SET dia_ordem = %s WHERE id = %s::uuid",
                    (entry.dia_ordem, entry.diario_id),
                )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()
