"""
scripts/import_listas.py

Importa dois CSVs do Letterboxd como projetos no banco:
  - clone-do-top-500.csv      → "Letterboxd Top 500"
  - clone-dos-1001-filmes.csv → "1001 Filmes para ver antes de morrer"

Para filmes já no banco (matched por letterboxd_uri): só vincula ao projeto.
Para filmes novos: busca no TMDB, cria no banco, depois vincula.
Idempotente — roda quantas vezes quiser sem duplicar projetos ou vínculos.

Uso:
    poetry run python scripts/import_listas.py
"""
import csv
import io
import os
import time
from pathlib import Path

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv

load_dotenv()

DB_USER     = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_NAME     = os.getenv("DB_NAME", "fiscal")
TMDB_KEY    = os.getenv("TMDB_API_KEY", "")

ROOT_DIR    = Path(__file__).parent.parent
DATA_DIR    = ROOT_DIR / "data" / "letterboxd-mbarreto-2026-04-26-23-15-utc"
POSTERS_DIR = ROOT_DIR / "data" / "images" / "posters"
TMDB_BASE   = "https://api.themoviedb.org/3"
TMDB_IMG    = "https://image.tmdb.org/t/p/w500"

POSTERS_DIR.mkdir(parents=True, exist_ok=True)

LISTAS = [
    {
        "csv":    "lists/clone-do-top-500.csv",
        "titulo": "Letterboxd Top 500",
        "cor":    "#e8c547",
    },
    {
        "csv":    "lists/clone-dos-1001-filmes.csv",
        "titulo": "1001 Filmes para ver antes de morrer",
        "cor":    "#c0392b",
    },
]


def dict_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


# ── TMDB ──────────────────────────────────────────────────────────────────────

def _tmdb(path, params=None):
    r = requests.get(
        f"{TMDB_BASE}{path}",
        params={"api_key": TMDB_KEY, **(params or {})},
        timeout=10,
    )
    r.raise_for_status()
    time.sleep(0.12)
    return r.json()


def _load_genres():
    data = _tmdb("/genre/movie/list", {"language": "en-US"})
    return {g["id"]: g["name"] for g in data.get("genres", [])}


def _download_poster(poster_path_tmdb):
    if not poster_path_tmdb:
        return None
    filename = poster_path_tmdb.lstrip("/")
    local = POSTERS_DIR / filename
    if local.exists():
        return f"data/images/posters/{filename}"
    try:
        r = requests.get(f"{TMDB_IMG}{poster_path_tmdb}", timeout=15)
        r.raise_for_status()
        local.write_bytes(r.content)
        time.sleep(0.12)
        return f"data/images/posters/{filename}"
    except Exception:
        return None


def _titulo(details, best, fallback):
    orig_lang = details.get("original_language") or best.get("original_language", "en")
    if orig_lang == "pt":
        return details.get("original_title") or best.get("original_title") or fallback
    return details.get("title") or best.get("title") or fallback


def _search_tmdb(name, year, genres_map):
    data = _tmdb("/search/movie", {"query": name, "year": year, "language": "en-US"})
    results = data.get("results") or []
    if not results:
        data = _tmdb("/search/movie", {"query": name, "language": "en-US"})
        results = data.get("results") or []
    if not results:
        return None

    best    = results[0]
    tmdb_id = best["id"]
    details    = _tmdb(f"/movie/{tmdb_id}", {"language": "en-US"})
    details_pt = _tmdb(f"/movie/{tmdb_id}", {"language": "pt-BR"})

    poster_tmdb  = details.get("poster_path") or best.get("poster_path")
    poster_local = _download_poster(poster_tmdb)

    genre_ids = details.get("genre_ids") or best.get("genre_ids") or []
    generos   = [genres_map[gid] for gid in genre_ids if gid in genres_map]

    release = details.get("release_date") or best.get("release_date") or ""
    ano = int(release[:4]) if len(release) >= 4 else (int(year) if year else None)

    return {
        "tmdb_id":         tmdb_id,
        "titulo":          _titulo(details, best, name),
        "titulo_pt":       details_pt.get("title"),
        "titulo_original": details.get("original_title"),
        "ano":             ano,
        "duracao_min":     details.get("runtime"),
        "genero":          generos,
        "sinopse":         details.get("overview") or best.get("overview"),
        "tagline":         details.get("tagline") or None,
        "nota_tmdb":       details.get("vote_average"),
        "votos_tmdb":      details.get("vote_count"),
        "poster_path":     poster_local,
    }


# ── CSV ───────────────────────────────────────────────────────────────────────

def _read_lista_csv(filename):
    """
    CSVs de lista do Letterboxd têm 4 linhas de cabeçalho antes dos dados:
      linha 1: versão do export
      linhas 2-3: metadados da lista
      linha 4: em branco
      linha 5: Position,Name,Year,URL,Description  ← cabeçalho real
      linha 6+: dados dos filmes
    """
    path = DATA_DIR / filename
    with open(path, encoding="utf-8", newline="") as f:
        lines = f.readlines()
    start = next(i for i, l in enumerate(lines) if l.strip().startswith("Position,"))
    return list(csv.DictReader(io.StringIO("".join(lines[start:]))))


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_or_create_projeto(conn, titulo, cor):
    with dict_cursor(conn) as cur:
        cur.execute("SELECT id FROM projeto WHERE titulo = %s", (titulo,))
        row = cur.fetchone()
    if row:
        return row["id"]
    with dict_cursor(conn) as cur:
        cur.execute(
            "INSERT INTO projeto (titulo, cor) VALUES (%s, %s) RETURNING id",
            (titulo, cor),
        )
        pid = cur.fetchone()["id"]
    conn.commit()
    print(f"  Projeto criado: \"{titulo}\" (id={pid})")
    return pid


def get_or_create_filme(conn, name, year, letterboxd_url, genres_map):
    """Retorna (filme_uuid, criado: bool)."""
    with dict_cursor(conn) as cur:
        cur.execute("SELECT id FROM filme WHERE letterboxd_uri = %s", (letterboxd_url,))
        row = cur.fetchone()
    if row:
        return str(row["id"]), False

    tmdb = None
    if TMDB_KEY:
        try:
            tmdb = _search_tmdb(name, year, genres_map)
        except Exception as e:
            print(f" [TMDB erro: {e}]", end="")

    if tmdb:
        vals = (
            tmdb["titulo"] or name,
            tmdb.get("titulo_pt"),
            tmdb["titulo_original"],
            tmdb["ano"] or (int(year) if year else None),
            tmdb["duracao_min"],
            tmdb["genero"],
            tmdb["tmdb_id"],
            letterboxd_url,
            tmdb["sinopse"],
            tmdb["tagline"],
            tmdb["nota_tmdb"],
            tmdb["votos_tmdb"],
            tmdb["poster_path"],
        )
    else:
        vals = (
            name, None, None,
            int(year) if year else None,
            None, [],
            None, letterboxd_url,
            None, None, None, None, None,
        )

    with dict_cursor(conn) as cur:
        cur.execute("""
            INSERT INTO filme
                (titulo, titulo_pt, titulo_original, ano, duracao_min, genero,
                 tmdb_id, letterboxd_uri, sinopse, tagline,
                 nota_tmdb, votos_tmdb, poster_path)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (letterboxd_uri) DO UPDATE SET
                titulo     = EXCLUDED.titulo,
                updated_at = now()
            RETURNING id
        """, vals)
        film_id = str(cur.fetchone()["id"])
    conn.commit()
    return film_id, True


def link_filme(conn, projeto_id, filme_id, sort_order):
    with dict_cursor(conn) as cur:
        cur.execute("""
            INSERT INTO projeto_filme (projeto_id, filme_id, sort_order)
            VALUES (%s, %s::uuid, %s)
            ON CONFLICT (projeto_id, filme_id) DO NOTHING
        """, (projeto_id, filme_id, sort_order))
    conn.commit()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  IMPORT LISTAS -> Projetos")
    print("=" * 60)
    print(f"  Banco : {DB_USER}@{DB_HOST}/{DB_NAME}")
    print(f"  TMDB  : {'configurado' if TMDB_KEY else 'SEM CHAVE — filmes criados sem metadados'}")
    print()

    conn = psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        options="-c search_path=filmes",
    )
    conn.autocommit = False

    genres_map = {}
    if TMDB_KEY:
        print("Carregando gêneros TMDB...", end=" ", flush=True)
        genres_map = _load_genres()
        print(f"OK ({len(genres_map)} gêneros)")

    for lista in LISTAS:
        print(f"\n{'─' * 60}")
        print(f"  {lista['titulo']}")
        print(f"{'─' * 60}")

        rows = _read_lista_csv(lista["csv"])
        total = len(rows)
        print(f"  {total} filmes no CSV")

        projeto_id = get_or_create_projeto(conn, lista["titulo"], lista["cor"])
        print(f"  Projeto id={projeto_id}\n")

        novos = ja_existia = 0

        for row in rows:
            position = int(row["Position"])
            name     = row["Name"].strip()
            year     = row["Year"].strip()
            url      = row["URL"].strip()

            pct = position * 100 // total
            print(f"  [{position:>4}/{total}  {pct:>3}%] {name} ({year})", end=" ", flush=True)

            filme_id, criado = get_or_create_filme(conn, name, year, url, genres_map)
            if criado:
                novos += 1
                print("[novo]")
            else:
                ja_existia += 1
                print("[ok]")

            link_filme(conn, projeto_id, filme_id, position)

        print(f"\n  Resumo: {total} vinculados | {novos} criados | {ja_existia} já existiam")

    conn.close()
    print(f"\n{'=' * 60}")
    print("  CONCLUÍDO")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
