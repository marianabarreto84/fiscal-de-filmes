from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import requests
from backend.database import get_db, dict_cursor

TMDB_IMG_W  = "https://image.tmdb.org/t/p/w500"
POSTERS_DIR = Path(__file__).parent.parent.parent / "data" / "images" / "posters"
POSTERS_DIR.mkdir(parents=True, exist_ok=True)


def _download_poster(poster_url: str) -> Optional[str]:
    """Recebe a poster_url completa do TMDB, baixa e retorna o caminho relativo local."""
    try:
        filename = poster_url.rstrip("/").split("/")[-1]
        local = POSTERS_DIR / filename
        if not local.exists():
            r = requests.get(f"{TMDB_IMG_W}/{filename}", timeout=15)
            r.raise_for_status()
            local.write_bytes(r.content)
        return f"data/images/posters/{filename}"
    except Exception:
        return None

router = APIRouter()


class FilmeCreate(BaseModel):
    tmdb_id: str
    titulo: str
    titulo_original: Optional[str] = None
    duracao_min: Optional[int] = None
    sinopse: Optional[str] = None
    ano: Optional[int] = None
    nota_tmdb: Optional[float] = None
    poster_url: Optional[str] = None


class AssistirFilme(BaseModel):
    filme_id: Optional[str] = None   # UUID — vem também da rota, campo é opcional
    ano_assistido: Optional[int] = None
    mes_assistido: Optional[int] = None
    dia_assistido: Optional[int] = None
    hora_assistido: Optional[int] = None
    minuto_assistido: Optional[int] = None
    plataforma_id: Optional[str] = None   # UUID
    notas: Optional[str] = None
    rewatch: bool = False


@router.post("/posters/sync")
def sync_missing_posters():
    """Baixa posters para todos os filmes que ainda não têm arquivo local."""
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("""
                SELECT id, tmdb_id, titulo, poster_path
                FROM filme
                WHERE tmdb_id IS NOT NULL
                ORDER BY titulo
            """)
            filmes = cur.fetchall()

        ok = errors = skipped = 0
        for f in filmes:
            local_path = f["poster_path"]
            # Pula se já tem arquivo no disco
            if local_path and (Path(__file__).parent.parent.parent / local_path).exists():
                skipped += 1
                continue

            # Busca poster_path do TMDB
            try:
                import os, time
                token = os.getenv("TMDB_API_KEY", "")
                if not token:
                    errors += 1
                    continue
                r = requests.get(
                    f"https://api.themoviedb.org/3/movie/{f['tmdb_id']}",
                    params={"api_key": token, "language": "en-US"},
                    timeout=10,
                )
                r.raise_for_status()
                tmdb_poster = r.json().get("poster_path")
                time.sleep(0.12)
            except Exception:
                errors += 1
                continue

            if not tmdb_poster:
                errors += 1
                continue

            poster_url = f"https://image.tmdb.org/t/p/w342{tmdb_poster}"
            saved = _download_poster(poster_url)
            if saved:
                with dict_cursor(conn) as cur:
                    cur.execute(
                        "UPDATE filme SET poster_path = %s, updated_at = now() WHERE id = %s",
                        (saved, f["id"]),
                    )
                conn.commit()
                ok += 1
            else:
                errors += 1

        return {"ok": ok, "errors": errors, "skipped": skipped}
    finally:
        conn.close()


@router.get("")
def list_filmes():
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("""
                SELECT f.*,
                    EXISTS(SELECT 1 FROM diario d WHERE d.filme_id = f.id) AS assistido,
                    EXISTS(SELECT 1 FROM watchlist w WHERE w.filme_id = f.id) AS na_watchlist,
                    (SELECT MAX(d.assistido_em) FROM diario d WHERE d.filme_id = f.id) AS ultimo_assistido
                FROM filme f
                ORDER BY f.titulo
            """)
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/{filme_id}")
def get_filme(filme_id: str):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("""
                SELECT f.*,
                    EXISTS(SELECT 1 FROM diario d WHERE d.filme_id = f.id) AS assistido,
                    EXISTS(SELECT 1 FROM watchlist w WHERE w.filme_id = f.id) AS na_watchlist,
                    (SELECT nota FROM avaliacao WHERE filme_id = f.id) AS minha_nota
                FROM filme f
                WHERE f.id = %s::uuid
            """, (filme_id,))
            row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Filme não encontrado")

        with dict_cursor(conn) as cur:
            cur.execute("""
                SELECT d.*, p.nome AS plataforma_nome, p.logo_path AS plataforma_logo
                FROM diario d
                LEFT JOIN plataforma p ON p.id = d.plataforma_id
                WHERE d.filme_id = %s::uuid
                ORDER BY d.assistido_em DESC NULLS LAST
            """, (filme_id,))
            entradas = cur.fetchall()

        result = dict(row)
        result["diario"] = [dict(e) for e in entradas]
        return result
    finally:
        conn.close()


@router.post("")
def create_filme(body: FilmeCreate):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("SELECT id FROM filme WHERE tmdb_id = %s", (int(body.tmdb_id),))
            if cur.fetchone():
                raise HTTPException(400, "Filme já existe")

            cur.execute("""
                INSERT INTO filme (tmdb_id, titulo, titulo_original, duracao_min, sinopse, ano, nota_tmdb)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (int(body.tmdb_id), body.titulo, body.titulo_original,
                  body.duracao_min, body.sinopse, body.ano, body.nota_tmdb))
            filme_id = str(cur.fetchone()["id"])

        # Baixa poster se a URL foi fornecida
        poster_path = None
        if body.poster_url:
            poster_path = _download_poster(body.poster_url)
        if poster_path:
            with dict_cursor(conn) as cur:
                cur.execute(
                    "UPDATE filme SET poster_path = %s WHERE id = %s::uuid",
                    (poster_path, filme_id),
                )

        conn.commit()
        return {"id": filme_id, "message": "Filme criado"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        conn.close()


@router.delete("/{filme_id}")
def delete_filme(filme_id: str):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("DELETE FROM filme WHERE id = %s::uuid", (filme_id,))
        conn.commit()
        return {"message": "Deletado"}
    finally:
        conn.close()


@router.post("/{filme_id}/assistir")
def marcar_assistido(filme_id: str, body: AssistirFilme):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("SELECT id FROM filme WHERE id = %s::uuid", (filme_id,))
            if not cur.fetchone():
                raise HTTPException(404, "Filme não encontrado")

            cur.execute("""
                INSERT INTO diario
                    (filme_id, assistido_em, rewatch, hora_assistido, minuto_assistido, plataforma_id)
                VALUES (
                    %s::uuid,
                    CASE
                        WHEN %s IS NOT NULL AND %s IS NOT NULL AND %s IS NOT NULL
                        THEN make_date(%s, %s, %s)
                        ELSE NULL
                    END,
                    %s, %s, %s,
                    %s::uuid
                )
                RETURNING id
            """, (
                filme_id,
                body.ano_assistido, body.mes_assistido, body.dia_assistido,
                body.ano_assistido, body.mes_assistido, body.dia_assistido,
                body.rewatch,
                body.hora_assistido, body.minuto_assistido,
                body.plataforma_id,
            ))
            diario_id = str(cur.fetchone()["id"])

            cur.execute("DELETE FROM watchlist WHERE filme_id = %s::uuid", (filme_id,))

        conn.commit()
        return {"id": diario_id, "message": "Marcado como assistido"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        conn.close()


@router.delete("/{filme_id}/assistir")
def desmarcar_assistido(filme_id: str):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("DELETE FROM diario WHERE filme_id = %s::uuid", (filme_id,))
        conn.commit()
        return {"message": "Desmarcado"}
    finally:
        conn.close()


@router.delete("/{filme_id}/assistir/{diario_id}")
def remover_entrada_diario(filme_id: str, diario_id: str):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute(
                "DELETE FROM diario WHERE id = %s::uuid AND filme_id = %s::uuid",
                (diario_id, filme_id),
            )
        conn.commit()
        return {"message": "Entrada removida"}
    finally:
        conn.close()


@router.post("/{filme_id}/watchlist")
def add_watchlist(filme_id: str):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("SELECT id FROM filme WHERE id = %s::uuid", (filme_id,))
            if not cur.fetchone():
                raise HTTPException(404, "Filme não encontrado")

            cur.execute("""
                INSERT INTO watchlist (filme_id) VALUES (%s::uuid)
                ON CONFLICT (filme_id) DO NOTHING
            """, (filme_id,))
        conn.commit()
        return {"message": "Adicionado à watchlist"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        conn.close()


@router.delete("/{filme_id}/watchlist")
def remove_watchlist(filme_id: str):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("DELETE FROM watchlist WHERE filme_id = %s::uuid", (filme_id,))
        conn.commit()
        return {"message": "Removido da watchlist"}
    finally:
        conn.close()
