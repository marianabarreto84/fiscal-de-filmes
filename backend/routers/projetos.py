from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from backend.database import get_db, dict_cursor

router = APIRouter()


class ProjetoCreate(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    cor: Optional[str] = "#6366f1"


class ProjetoUpdate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    cor: Optional[str] = None


class AddFilmes(BaseModel):
    filme_ids: List[str]   # UUIDs


@router.get("")
def list_projetos():
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("SELECT * FROM projeto ORDER BY criado_em DESC")
            rows = cur.fetchall()

        result = []
        for p in rows:
            p = dict(p)
            with dict_cursor(conn) as cur:
                cur.execute("""
                    SELECT COUNT(DISTINCT pf.filme_id) AS total_filmes,
                           COUNT(DISTINCT d.filme_id)  AS filmes_assistidos
                    FROM projeto_filme pf
                    LEFT JOIN diario d ON d.filme_id = pf.filme_id
                    WHERE pf.projeto_id = %s
                """, (p["id"],))
                stats = cur.fetchone()
            p.update(dict(stats))
            result.append(p)

        return result
    finally:
        conn.close()


@router.post("")
def create_projeto(body: ProjetoCreate):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute(
                "INSERT INTO projeto (titulo, descricao, cor) VALUES (%s, %s, %s) RETURNING id",
                (body.titulo, body.descricao, body.cor),
            )
            pid = cur.fetchone()["id"]
        conn.commit()
        return {"id": pid, "message": "Projeto criado"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        conn.close()


@router.get("/{projeto_id}")
def get_projeto(projeto_id: int):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("SELECT * FROM projeto WHERE id = %s", (projeto_id,))
            p = cur.fetchone()
        if not p:
            raise HTTPException(404, "Projeto não encontrado")
        p = dict(p)

        with dict_cursor(conn) as cur:
            cur.execute("""
                SELECT f.*, pf.sort_order, pf.adicionado_em,
                       EXISTS(SELECT 1 FROM diario d WHERE d.filme_id = f.id) AS assistido,
                       (SELECT nota FROM avaliacao WHERE filme_id = f.id) AS minha_nota
                FROM projeto_filme pf
                JOIN filme f ON f.id = pf.filme_id
                WHERE pf.projeto_id = %s
                ORDER BY pf.sort_order, pf.adicionado_em
            """, (projeto_id,))
            filmes_rows = cur.fetchall()

        p["items"] = [dict(r) for r in filmes_rows]

        with dict_cursor(conn) as cur:
            cur.execute("""
                SELECT COUNT(DISTINCT pf.filme_id) AS total_filmes,
                       COUNT(DISTINCT d.filme_id)  AS filmes_assistidos,
                       COALESCE(SUM(f.duracao_min), 0) AS total_minutos,
                       COALESCE(SUM(CASE WHEN d.filme_id IS NOT NULL THEN f.duracao_min ELSE 0 END), 0) AS minutos_assistidos
                FROM projeto_filme pf
                JOIN filme f ON f.id = pf.filme_id
                LEFT JOIN diario d ON d.filme_id = pf.filme_id
                WHERE pf.projeto_id = %s
            """, (projeto_id,))
            stats = cur.fetchone()

        p.update(dict(stats))
        return p
    finally:
        conn.close()


@router.put("/{projeto_id}")
def update_projeto(projeto_id: int, body: ProjetoUpdate):
    conn = get_db()
    try:
        fields = {k: v for k, v in body.dict().items() if v is not None}
        if fields:
            sets = ", ".join(f"{k} = %s" for k in fields)
            with dict_cursor(conn) as cur:
                cur.execute(
                    f"UPDATE projeto SET {sets} WHERE id = %s",
                    (*fields.values(), projeto_id),
                )
            conn.commit()
        return {"message": "Atualizado"}
    finally:
        conn.close()


@router.delete("/{projeto_id}")
def delete_projeto(projeto_id: int):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("DELETE FROM projeto WHERE id = %s", (projeto_id,))
        conn.commit()
        return {"message": "Deletado"}
    finally:
        conn.close()


@router.post("/{projeto_id}/filmes")
def add_filmes_to_projeto(projeto_id: int, body: AddFilmes):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute(
                "SELECT COALESCE(MAX(sort_order), 0) AS max_order FROM projeto_filme WHERE projeto_id = %s",
                (projeto_id,),
            )
            max_order = cur.fetchone()["max_order"]

            for i, fid in enumerate(body.filme_ids):
                cur.execute("""
                    INSERT INTO projeto_filme (projeto_id, filme_id, sort_order)
                    VALUES (%s, %s::uuid, %s)
                    ON CONFLICT (projeto_id, filme_id) DO NOTHING
                """, (projeto_id, fid, max_order + i + 1))
        conn.commit()
        return {"message": "Adicionados"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        conn.close()


@router.delete("/{projeto_id}/filmes/{filme_id}")
def remove_filme_from_projeto(projeto_id: int, filme_id: str):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute(
                "DELETE FROM projeto_filme WHERE projeto_id = %s AND filme_id = %s::uuid",
                (projeto_id, filme_id),
            )
        conn.commit()
        return {"message": "Removido"}
    finally:
        conn.close()
