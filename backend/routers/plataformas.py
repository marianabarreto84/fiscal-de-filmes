"""
backend/routers/plataformas.py

Tabelas:
  plataforma        — catálogo global (id UUID, nome, logo, região)
  plataforma_config — visibilidade (BOOLEAN) e ordem de exibição (INTEGER)
  filme_plataforma  — relação filme ↔ plataforma (UUIDs)
  filme_plataforma_padrao — plataforma padrão por filme
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import httpx
import os
import re

from backend.database import get_db, dict_cursor

LOGO_DIR = Path(__file__).parent.parent.parent / "data" / "images" / "providers"
LOGO_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter()

TMDB_BASE  = "https://api.themoviedb.org/3"
TMDB_IMAGE = "https://image.tmdb.org/t/p"
REGIONS    = ["BR", "US"]


class PlataformaAdd(BaseModel):
    plataforma_id: Optional[str] = None   # UUID
    nome:          Optional[str] = None
    tipo:          Optional[str] = "manual"

class PlataformaDefaultBody(BaseModel):
    plataforma_id: Optional[str] = None   # UUID, None = limpar

class PlataformaConfigPatch(BaseModel):
    visivel: Optional[bool] = None
    ordem:   Optional[int]  = None

class ReorderBody(BaseModel):
    plataforma_ids: list[str]   # UUIDs


def _logo(path: str) -> Optional[str]:
    return f"{TMDB_IMAGE}/w92{path}" if path else None

def _logo_filename(logo_url: str) -> Optional[str]:
    if not logo_url:
        return None
    m = re.search(r'/t/p/[^/]+/(.+)$', logo_url)
    return m.group(1) if m else None


async def _download_logo(logo_url: str) -> Optional[str]:
    filename = _logo_filename(logo_url)
    if not filename:
        return None
    dest = LOGO_DIR / filename
    if dest.exists():
        return f"/images/providers/{filename}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(logo_url)
            if r.status_code == 200:
                dest.write_bytes(r.content)
                return f"/images/providers/{filename}"
    except Exception:
        pass
    return None


async def _get_or_create_plataforma(conn, tmdb_provider_id, nome, regiao, logo_url) -> str:
    """Upsert plataforma e plataforma_config; retorna UUID como string."""
    logo_local = await _download_logo(logo_url) if logo_url else None

    with dict_cursor(conn) as cur:
        cur.execute("""
            INSERT INTO plataforma (nome, tmdb_provider_id, regiao, logo_url, logo_path)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (nome) DO UPDATE SET
                tmdb_provider_id = COALESCE(EXCLUDED.tmdb_provider_id, plataforma.tmdb_provider_id),
                logo_url         = COALESCE(EXCLUDED.logo_url,         plataforma.logo_url),
                logo_path        = COALESCE(EXCLUDED.logo_path,        plataforma.logo_path),
                updated_at       = now()
            RETURNING id
        """, (nome, tmdb_provider_id, regiao, logo_url, logo_local))
        plat_id = str(cur.fetchone()["id"])

        cur.execute("""
            INSERT INTO plataforma_config (plataforma_id, visivel, ordem)
            VALUES (%s::uuid, TRUE, 999)
            ON CONFLICT (plataforma_id) DO NOTHING
        """, (plat_id,))

    return plat_id


async def _fetch_providers_tmdb(tmdb_id: str) -> list[dict]:
    token = os.getenv("TMDB_API_KEY")
    if not token:
        raise HTTPException(500, "TMDB_API_KEY não configurada")

    url = f"{TMDB_BASE}/movie/{tmdb_id}/watch/providers"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params={"api_key": token}, timeout=10)

    if r.status_code == 404:
        return []
    if r.status_code != 200:
        raise HTTPException(r.status_code, f"Erro TMDB: {r.text}")

    data = r.json().get("results", {})
    providers = []
    seen = set()

    for region in REGIONS:
        region_data = data.get(region, {})
        for ptype in ("flatrate", "free", "rent", "buy"):
            for p in region_data.get(ptype, []):
                nome = f"{p['provider_name']} ({region})"
                if nome in seen:
                    continue
                seen.add(nome)
                providers.append({
                    "tmdb_provider_id": p["provider_id"],
                    "nome":             nome,
                    "regiao":           region,
                    "logo_url":         _logo(p.get("logo_path", "")),
                    "tipo":             ptype,
                })

    return providers


async def _upsert_filme_plataformas(conn, filme_id: str, providers: list[dict]) -> int:
    with dict_cursor(conn) as cur:
        cur.execute(
            "DELETE FROM filme_plataforma WHERE filme_id = %s::uuid AND fonte = 'tmdb'",
            (filme_id,),
        )

    count = 0
    for p in providers:
        pid = await _get_or_create_plataforma(
            conn, p["tmdb_provider_id"], p["nome"], p["regiao"], p["logo_url"]
        )
        try:
            with dict_cursor(conn) as cur:
                cur.execute("""
                    INSERT INTO filme_plataforma (filme_id, plataforma_id, tipo, fonte)
                    VALUES (%s::uuid, %s::uuid, %s, 'tmdb')
                    ON CONFLICT (filme_id, plataforma_id) DO UPDATE SET
                        tipo       = EXCLUDED.tipo,
                        fonte      = 'tmdb',
                        updated_at = now()
                """, (filme_id, pid, p["tipo"]))
            count += 1
        except Exception:
            pass

    return count


# ── Catálogo ──────────────────────────────────────────────────────────────────

@router.get("/catalog")
def get_catalog():
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("""
                SELECT p.id, p.tmdb_provider_id, p.nome, p.regiao,
                       p.logo_url, p.logo_path,
                       COALESCE(pc.visivel, TRUE)  AS visivel,
                       COALESCE(pc.ordem, 999)     AS ordem
                FROM plataforma p
                LEFT JOIN plataforma_config pc ON pc.plataforma_id = p.id
                ORDER BY COALESCE(pc.ordem, 999), p.nome
            """)
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Config ────────────────────────────────────────────────────────────────────

@router.get("/config")
def get_config():
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("""
                SELECT p.id, p.nome, p.regiao, p.logo_url, p.logo_path,
                       COALESCE(pc.visivel, TRUE) AS visivel,
                       COALESCE(pc.ordem, 999)    AS ordem
                FROM plataforma p
                LEFT JOIN plataforma_config pc ON pc.plataforma_id = p.id
                ORDER BY CASE WHEN COALESCE(pc.visivel, TRUE) THEN 0 ELSE 1 END,
                         COALESCE(pc.ordem, 999), p.nome
            """)
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.patch("/config/{plataforma_id}")
def patch_config(plataforma_id: str, body: PlataformaConfigPatch):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("SELECT id FROM plataforma WHERE id = %s::uuid", (plataforma_id,))
            if not cur.fetchone():
                raise HTTPException(404, "Plataforma não encontrada")
            cur.execute("""
                INSERT INTO plataforma_config (plataforma_id, visivel, ordem)
                VALUES (%s::uuid, COALESCE(%s, TRUE), COALESCE(%s, 999))
                ON CONFLICT (plataforma_id) DO UPDATE SET
                    visivel = COALESCE(%s, plataforma_config.visivel),
                    ordem   = COALESCE(%s, plataforma_config.ordem)
            """, (plataforma_id,
                  body.visivel, body.ordem,
                  body.visivel, body.ordem))
        conn.commit()
        return {"message": "ok"}
    finally:
        conn.close()


@router.post("/config/reorder")
def reorder_config(body: ReorderBody):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            for i, pid in enumerate(body.plataforma_ids):
                cur.execute("""
                    INSERT INTO plataforma_config (plataforma_id, visivel, ordem)
                    VALUES (%s::uuid, TRUE, %s)
                    ON CONFLICT (plataforma_id) DO UPDATE SET ordem = EXCLUDED.ordem
                """, (pid, i))
        conn.commit()
        return {"message": "ok"}
    finally:
        conn.close()


# ── Endpoints: filme ──────────────────────────────────────────────────────────

@router.get("/filme/{filme_id}")
def get_filme_plataformas_visible(filme_id: str):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("""
                SELECT p.id, p.nome, p.regiao, p.logo_url, p.logo_path,
                       fp.tipo, fp.fonte,
                       COALESCE(pc.ordem, 999) AS ordem
                FROM filme_plataforma fp
                JOIN plataforma p ON p.id = fp.plataforma_id
                LEFT JOIN plataforma_config pc ON pc.plataforma_id = p.id
                WHERE fp.filme_id = %s::uuid
                  AND COALESCE(pc.visivel, TRUE)
                ORDER BY COALESCE(pc.ordem, 999), p.nome
            """, (filme_id,))
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/filme/{filme_id}/all")
def get_filme_plataformas_all(filme_id: str):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("""
                SELECT p.id, p.nome, p.regiao, p.logo_url, p.logo_path,
                       fp.tipo, fp.fonte,
                       COALESCE(pc.visivel, TRUE) AS visivel,
                       COALESCE(pc.ordem, 999)    AS ordem
                FROM filme_plataforma fp
                JOIN plataforma p ON p.id = fp.plataforma_id
                LEFT JOIN plataforma_config pc ON pc.plataforma_id = p.id
                WHERE fp.filme_id = %s::uuid
                ORDER BY COALESCE(pc.ordem, 999), p.nome
            """, (filme_id,))
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.post("/filme/{filme_id}")
async def add_plataforma_to_filme(filme_id: str, body: PlataformaAdd):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("SELECT id FROM filme WHERE id = %s::uuid", (filme_id,))
            if not cur.fetchone():
                raise HTTPException(404, "Filme não encontrado")

        if body.plataforma_id:
            pid = body.plataforma_id
            with dict_cursor(conn) as cur:
                cur.execute("SELECT id FROM plataforma WHERE id = %s::uuid", (pid,))
                if not cur.fetchone():
                    raise HTTPException(404, "Plataforma não encontrada no catálogo")
        elif body.nome:
            pid = await _get_or_create_plataforma(conn, None, body.nome.strip(), None, None)
        else:
            raise HTTPException(400, "Informe plataforma_id ou nome")

        with dict_cursor(conn) as cur:
            cur.execute("""
                INSERT INTO filme_plataforma (filme_id, plataforma_id, tipo, fonte)
                VALUES (%s::uuid, %s::uuid, %s, 'manual')
                ON CONFLICT (filme_id, plataforma_id) DO NOTHING
            """, (filme_id, pid, body.tipo or "manual"))

        conn.commit()
        return {"message": "Plataforma adicionada", "plataforma_id": pid}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(400, str(e))
    finally:
        conn.close()


@router.delete("/filme/{filme_id}/{plataforma_id}")
def remove_plataforma_from_filme(filme_id: str, plataforma_id: str):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute(
                "DELETE FROM filme_plataforma WHERE filme_id = %s::uuid AND plataforma_id = %s::uuid",
                (filme_id, plataforma_id),
            )
        conn.commit()
        return {"message": "Removida"}
    finally:
        conn.close()


# ── Defaults ──────────────────────────────────────────────────────────────────

@router.get("/defaults")
def get_all_defaults():
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("""
                SELECT f.id, f.titulo, f.poster_path,
                       fpd.plataforma_id AS default_plataforma_id
                FROM filme f
                LEFT JOIN filme_plataforma_padrao fpd ON fpd.filme_id = f.id
                ORDER BY f.titulo
            """)
            filmes_rows = cur.fetchall()

            cur.execute("""
                SELECT fp.filme_id, p.id, p.nome
                FROM filme_plataforma fp
                JOIN plataforma p ON p.id = fp.plataforma_id
                LEFT JOIN plataforma_config pc ON pc.plataforma_id = p.id
                WHERE COALESCE(pc.visivel, TRUE)
                ORDER BY COALESCE(pc.ordem, 999), p.nome
            """)
            plat_rows = cur.fetchall()

        plats_by_filme: dict = {}
        for r in plat_rows:
            key = str(r["filme_id"])
            plats_by_filme.setdefault(key, []).append(
                {"id": str(r["id"]), "nome": r["nome"]}
            )

        return [
            {
                "filme_id":              str(f["id"]),
                "filme_titulo":          f["titulo"],
                "poster_path":           f["poster_path"],
                "plataformas":           plats_by_filme.get(str(f["id"]), []),
                "default_plataforma_id": str(f["default_plataforma_id"]) if f["default_plataforma_id"] else None,
            }
            for f in filmes_rows
        ]
    finally:
        conn.close()


@router.get("/defaults/{filme_id}")
def get_filme_default(filme_id: str):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute(
                "SELECT plataforma_id FROM filme_plataforma_padrao WHERE filme_id = %s::uuid",
                (filme_id,),
            )
            row = cur.fetchone()
        return {"plataforma_id": str(row["plataforma_id"]) if row and row["plataforma_id"] else None}
    finally:
        conn.close()


@router.put("/defaults/{filme_id}")
def set_filme_default(filme_id: str, body: PlataformaDefaultBody):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("SELECT id FROM filme WHERE id = %s::uuid", (filme_id,))
            if not cur.fetchone():
                raise HTTPException(404, "Filme não encontrado")

            if body.plataforma_id is None:
                cur.execute(
                    "DELETE FROM filme_plataforma_padrao WHERE filme_id = %s::uuid", (filme_id,)
                )
            else:
                cur.execute("""
                    INSERT INTO filme_plataforma_padrao (filme_id, plataforma_id)
                    VALUES (%s::uuid, %s::uuid)
                    ON CONFLICT (filme_id) DO UPDATE SET plataforma_id = EXCLUDED.plataforma_id
                """, (filme_id, body.plataforma_id))

        conn.commit()
        return {"message": "ok"}
    finally:
        conn.close()


# ── Sync TMDB ─────────────────────────────────────────────────────────────────

@router.get("/preview/{filme_id}")
async def preview_plataformas_for_filme(filme_id: str):
    """Consulta o TMDB e retorna o que seria sincronizado, sem salvar nada."""
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute(
                "SELECT id, tmdb_id, titulo FROM filme WHERE id = %s::uuid", (filme_id,)
            )
            f = cur.fetchone()
        if not f:
            raise HTTPException(404, "Filme não encontrado")
        if not f["tmdb_id"]:
            return {"providers": [], "titulo": f["titulo"], "message": "Sem tmdb_id"}

        providers = await _fetch_providers_tmdb(str(f["tmdb_id"]))

        result = []
        with dict_cursor(conn) as cur:
            for p in providers:
                cur.execute("""
                    SELECT pl.id, pl.logo_path,
                           COALESCE(pc.visivel, TRUE) AS visivel
                    FROM plataforma pl
                    LEFT JOIN plataforma_config pc ON pc.plataforma_id = pl.id
                    WHERE pl.nome = %s
                """, (p["nome"],))
                row = cur.fetchone()
                result.append({
                    "nome":      p["nome"],
                    "logo_url":  p.get("logo_url"),
                    "logo_path": row["logo_path"] if row else None,
                    "visivel":   bool(row["visivel"]) if row else True,
                })

        return {"providers": result, "titulo": f["titulo"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        conn.close()


@router.post("/sync/{filme_id}")
async def sync_plataformas_for_filme(filme_id: str):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute(
                "SELECT id, tmdb_id, titulo FROM filme WHERE id = %s::uuid", (filme_id,)
            )
            f = cur.fetchone()
        if not f:
            raise HTTPException(404, "Filme não encontrado")
        if not f["tmdb_id"]:
            return {"filme_id": filme_id, "synced": 0, "message": "Sem tmdb_id"}

        providers = await _fetch_providers_tmdb(str(f["tmdb_id"]))
        count = await _upsert_filme_plataformas(conn, filme_id, providers)
        conn.commit()
        return {"filme_id": filme_id, "titulo": f["titulo"], "synced": count, "found": len(providers)}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        conn.close()


@router.post("/sync-all")
async def sync_all_plataformas():
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("SELECT id, tmdb_id, titulo FROM filme WHERE tmdb_id IS NOT NULL")
            all_filmes = cur.fetchall()

        results, errors = [], []
        for f in all_filmes:
            try:
                providers = await _fetch_providers_tmdb(str(f["tmdb_id"]))
                count = await _upsert_filme_plataformas(conn, str(f["id"]), providers)
                results.append({"filme_id": str(f["id"]), "titulo": f["titulo"], "synced": count})
            except Exception as e:
                errors.append({"filme_id": str(f["id"]), "titulo": f["titulo"], "error": str(e)})

        conn.commit()
        return {
            "total": len(all_filmes), "ok": len(results), "errors": len(errors),
            "results": results, "failed": errors,
        }
    finally:
        conn.close()
