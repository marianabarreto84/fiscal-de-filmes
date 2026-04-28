"""
Sincroniza watchlist e status de assistido a partir dos CSVs do Letterboxd.

Match primário:  letterboxd_uri (filmes importados pelo import_pg.py)
Match secundário: (titulo_lower, ano) — fallback para filmes adicionados manualmente

Idempotente: pode rodar múltiplas vezes sem duplicar dados.
"""

import csv
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DB_USER     = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_NAME     = os.getenv("DB_NAME", "fiscal")

DATA_DIR = Path(__file__).parent / "data" / "letterboxd-mbarreto-2026-04-26-23-15-utc"


def get_conn():
    return psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        options="-c search_path=filmes",
    )


def _csv(filename):
    with open(DATA_DIR / filename, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _dt(s):
    if not s or not s.strip():
        return None
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _date(s):
    if not s or not s.strip():
        return None
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _rating(s):
    if not s or not s.strip():
        return None
    try:
        return float(s.strip())
    except ValueError:
        return None


def build_lookups(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, letterboxd_uri,
                   LOWER(titulo)                         AS titulo_l,
                   LOWER(COALESCE(titulo_original, '')) AS titulo_orig_l,
                   LOWER(COALESCE(titulo_pt, ''))       AS titulo_pt_l,
                   ano
            FROM filme
        """)
        rows = cur.fetchall()

    uri_to_id    = {}
    title_groups = {}   # (titulo_lower, ano_str) → [film_id, ...]

    for film_id, lboxd_uri, titulo_l, titulo_orig_l, titulo_pt_l, ano in rows:
        if lboxd_uri:
            uri_to_id[lboxd_uri] = film_id
        ano_s = str(ano) if ano else ''
        for key in {(titulo_l, ano_s), (titulo_orig_l, ano_s), (titulo_pt_l, ano_s)}:
            if key[0]:
                title_groups.setdefault(key, []).append(film_id)

    # Só usa match por título quando é inequívoco
    title_to_id = {k: v[0] for k, v in title_groups.items() if len(v) == 1}
    return uri_to_id, title_to_id


def find_film(row, uri_to_id, title_to_id):
    uri = row.get("Letterboxd URI", "").strip()
    if uri and uri in uri_to_id:
        return uri_to_id[uri], "uri"
    name = row.get("Name", "").strip().lower()
    year = row.get("Year", "").strip()
    fid = title_to_id.get((name, year))
    if fid:
        return fid, "titulo"
    return None, None


def main():
    print("Conectando ao banco...")
    conn = get_conn()
    uri_to_id, title_to_id = build_lookups(conn)
    print(f"  {len(uri_to_id)} filmes com letterboxd_uri | {len(title_to_id)} pares título+ano únicos\n")

    # ── 1. Entradas do diário ─────────────────────────────────────────────────
    print("── Diário (diary.csv) ──────────────────────────────────────────")
    n_ok = n_skip = n_miss = 0
    for row in _csv("diary.csv"):
        film_id, method = find_film(row, uri_to_id, title_to_id)
        if not film_id:
            n_miss += 1
            continue

        rewatch      = row.get("Rewatch", "").strip().lower() == "yes"
        assistido_em = _date(row.get("Watched Date", "").strip())
        avaliado_em  = _dt(row["Date"])
        nota         = _rating(row.get("Rating"))
        tags_raw     = row.get("Tags", "").strip()
        tags         = [t.strip() for t in tags_raw.split(",") if t.strip()] or None

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO diario
                    (filme_id, assistido_em, rewatch, tags, nota, avaliado_em)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (filme_id, avaliado_em) DO NOTHING
            """, (film_id, assistido_em, rewatch, tags, nota, avaliado_em))
            inserted = cur.rowcount
        conn.commit()

        if inserted:
            n_ok += 1
            rewatch_s = " [rewatch]" if rewatch else ""
            print(f"  + {row['Name'][:45]:<45} {row.get('Watched Date','')}  [{method}]{rewatch_s}")
        else:
            n_skip += 1

    print(f"\n  Inseridos: {n_ok} | Já existiam: {n_skip} | Não encontrados: {n_miss}\n")

    # ── 2. Watched (garante pelo menos 1 entrada no diário) ───────────────────
    print("── Assistidos (watched.csv) ────────────────────────────────────")

    # Constrói mapa URI -> data do diary (Watched Date se disponível, senão Date do log)
    # Filmes só em watched.csv não têm data confiável: o "Date" é apenas a data do log.
    diary_dates: dict[str, str] = {}
    diary_uris: set[str] = set()
    for row in _csv("diary.csv"):
        uri = row["Letterboxd URI"].strip()
        wd  = row.get("Watched Date", "").strip()
        dt  = row.get("Date", "").strip()
        diary_uris.add(uri)
        if uri not in diary_dates:
            diary_dates[uri] = wd or dt

    n_ok = n_skip = n_miss = 0
    for row in _csv("watched.csv"):
        film_id, method = find_film(row, uri_to_id, title_to_id)
        if not film_id:
            n_miss += 1
            continue

        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM diario WHERE filme_id = %s LIMIT 1", (film_id,))
            if cur.fetchone():
                n_skip += 1
                continue

        uri      = row.get("Letterboxd URI", "").strip()
        # Só usa data se o filme tiver entrada no diary; caso contrário assistido_em = NULL
        date_str = diary_dates.get(uri) if uri in diary_uris else None

        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO diario (filme_id, assistido_em) VALUES (%s, %s)",
                (film_id, _date(date_str) if date_str else None),
            )
        conn.commit()
        n_ok += 1
        print(f"  + {row['Name'][:45]:<45} {date_str or '(sem data)'}  [{method}]")

    print(f"\n  Inseridos: {n_ok} | Já tinham diário: {n_skip} | Não encontrados: {n_miss}\n")

    # ── 3. Watchlist ─────────────────────────────────────────────────────────
    print("── Watchlist (watchlist.csv) ────────────────────────────────────")
    n_ok = n_skip_watched = n_skip_exists = n_miss = 0
    for row in _csv("watchlist.csv"):
        film_id, method = find_film(row, uri_to_id, title_to_id)
        if not film_id:
            n_miss += 1
            continue

        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM diario WHERE filme_id = %s LIMIT 1", (film_id,))
            if cur.fetchone():
                n_skip_watched += 1
                continue

            cur.execute("""
                INSERT INTO watchlist (filme_id, adicionado_em)
                VALUES (%s, %s)
                ON CONFLICT (filme_id) DO NOTHING
            """, (film_id, _dt(row["Date"])))
            inserted = cur.rowcount
        conn.commit()

        if inserted:
            n_ok += 1
            print(f"  + {row['Name'][:50]:<50}  [{method}]")
        else:
            n_skip_exists += 1

    print(f"\n  Inseridos: {n_ok} | Já assistidos (ignorado): {n_skip_watched} | Já na watchlist: {n_skip_exists} | Não encontrados: {n_miss}\n")

    # ── Resumo final ─────────────────────────────────────────────────────────
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT
                COUNT(*) FILTER (
                    WHERE NOT EXISTS(SELECT 1 FROM diario d WHERE d.filme_id = f.id)
                      AND NOT EXISTS(SELECT 1 FROM watchlist w WHERE w.filme_id = f.id)
                ) AS sem_categoria,
                COUNT(*) FILTER (
                    WHERE EXISTS(SELECT 1 FROM diario d WHERE d.filme_id = f.id)
                ) AS assistidos,
                COUNT(*) FILTER (
                    WHERE EXISTS(SELECT 1 FROM watchlist w WHERE w.filme_id = f.id)
                      AND NOT EXISTS(SELECT 1 FROM diario d WHERE d.filme_id = f.id)
                ) AS quero_assistir,
                COUNT(*) AS total
            FROM filme f
        """)
        r = cur.fetchone()

    print("═" * 50)
    print(f"  Sem categoria : {r['sem_categoria']}")
    print(f"  Assistidos    : {r['assistidos']}")
    print(f"  Quero assistir: {r['quero_assistir']}")
    print(f"  Total         : {r['total']}")
    print("═" * 50)

    conn.close()


if __name__ == "__main__":
    main()
