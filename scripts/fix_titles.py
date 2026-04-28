"""Corrige títulos dos filmes já no banco para inglês (ou português para filmes nacionais)."""

import os
import time

import psycopg
import requests
from dotenv import load_dotenv

load_dotenv()

DB_USER     = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_NAME     = os.getenv("DB_NAME", "fiscal")
TMDB_KEY    = os.getenv("TMDB_API_KEY", "")
TMDB_BASE   = "https://api.themoviedb.org/3"


def _tmdb(path, params=None):
    r = requests.get(
        f"{TMDB_BASE}{path}",
        params={"api_key": TMDB_KEY, **(params or {})},
        timeout=10,
    )
    r.raise_for_status()
    time.sleep(0.12)
    return r.json()


def _titulo_correto(details):
    orig_lang = details.get("original_language", "en")
    if orig_lang == "pt":
        return details.get("original_title") or details.get("title")
    return details.get("title")


def main():
    conn = psycopg.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)

    with conn.cursor() as cur:
        cur.execute("SELECT id, tmdb_id, titulo FROM filmes.filme WHERE tmdb_id IS NOT NULL ORDER BY titulo")
        filmes = cur.fetchall()

    total = len(filmes)
    print(f"{total} filmes para verificar\n")

    atualizados = 0
    for i, (film_id, tmdb_id, titulo_atual) in enumerate(filmes, 1):
        endpoint = "movie"
        try:
            details_en = _tmdb(f"/movie/{tmdb_id}", {"language": "en-US"})
        except Exception:
            try:
                details_en = _tmdb(f"/tv/{tmdb_id}", {"language": "en-US"})
                endpoint = "tv"
            except Exception as e:
                print(f"[{i}/{total}] tmdb#{tmdb_id} — erro: {e}")
                continue

        try:
            details_pt = _tmdb(f"/{endpoint}/{tmdb_id}", {"language": "pt-BR"})
        except Exception:
            details_pt = {}

        novo_titulo = _titulo_correto(details_en)
        titulo_pt   = details_pt.get("title") or details_pt.get("name")

        mudou = novo_titulo and novo_titulo != titulo_atual
        label = f"{titulo_atual[:35]:<35}"
        if mudou:
            label += f" -> {novo_titulo}"
        if titulo_pt:
            label += f"  [pt: {titulo_pt}]"

        print(f"[{i}/{total}] {label}")

        if novo_titulo or titulo_pt:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE filmes.filme
                       SET titulo    = COALESCE(%s, titulo),
                           titulo_pt = COALESCE(%s, titulo_pt),
                           updated_at = now()
                       WHERE id = %s""",
                    (novo_titulo if mudou else None, titulo_pt or None, film_id),
                )
            conn.commit()
            if mudou:
                atualizados += 1

    conn.close()
    print(f"\n{atualizados} títulos principais corrigidos de {total}")


if __name__ == "__main__":
    main()
