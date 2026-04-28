"""Import Letterboxd CSV data into the fiscal PostgreSQL database (filmes schema)."""

import csv
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import requests
from dotenv import load_dotenv

load_dotenv()

DB_USER     = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_NAME     = os.getenv("DB_NAME", "fiscal")
TMDB_KEY    = os.getenv("TMDB_API_KEY", "")

DATA_DIR      = Path(__file__).parent / "data" / "letterboxd-mbarreto-2026-04-26-23-15-utc"
POSTERS_DIR   = Path(__file__).parent / "data" / "images" / "posters"
PROVIDERS_DIR = Path(__file__).parent / "data" / "images" / "providers"
TMDB_BASE     = "https://api.themoviedb.org/3"
TMDB_IMG      = "https://image.tmdb.org/t/p/w500"
TMDB_LOGO     = "https://image.tmdb.org/t/p/w92"
REGIONS       = ["BR", "US"]

POSTERS_DIR.mkdir(parents=True, exist_ok=True)
PROVIDERS_DIR.mkdir(parents=True, exist_ok=True)


# ── TMDB helpers ──────────────────────────────────────────────────────────────

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
    movie = _tmdb("/genre/movie/list", {"language": "en-US"})
    tv    = _tmdb("/genre/tv/list",    {"language": "en-US"})
    genres = {g["id"]: g["name"] for g in movie.get("genres", [])}
    genres.update({g["id"]: g["name"] for g in tv.get("genres", [])})
    return genres


def _titulo(details, best, fallback):
    """Retorna título em inglês, exceto para filmes originalmente em português."""
    orig_lang = details.get("original_language") or best.get("original_language", "en")
    if orig_lang == "pt":
        return details.get("original_title") or best.get("original_title") or fallback
    return details.get("title") or best.get("title") or fallback


def _download_poster(poster_path_tmdb):
    filename = poster_path_tmdb.lstrip("/")
    local = POSTERS_DIR / filename
    if local.exists():
        return str(local.relative_to(Path(__file__).parent))
    try:
        r = requests.get(f"{TMDB_IMG}{poster_path_tmdb}", timeout=15)
        r.raise_for_status()
        local.write_bytes(r.content)
        time.sleep(0.12)
        return str(local.relative_to(Path(__file__).parent))
    except Exception:
        return None


def _search_tmdb(title, year, genres_map):
    """Return enriched dict for a movie or None if not found."""
    data = _tmdb("/search/movie", {"query": title, "year": year, "language": "en-US"})
    results = data.get("results") or []
    if not results:
        data = _tmdb("/search/movie", {"query": title, "language": "en-US"})
        results = data.get("results") or []
    if not results:
        return None

    best = results[0]
    tmdb_id = best["id"]
    details    = _tmdb(f"/movie/{tmdb_id}", {"language": "en-US"})
    details_pt = _tmdb(f"/movie/{tmdb_id}", {"language": "pt-BR"})

    poster_tmdb = details.get("poster_path") or best.get("poster_path")
    poster_local = _download_poster(poster_tmdb) if poster_tmdb else None

    genre_ids = details.get("genre_ids") or best.get("genre_ids") or []
    generos = [genres_map[gid] for gid in genre_ids if gid in genres_map]

    release = details.get("release_date") or best.get("release_date") or ""
    ano = int(release[:4]) if len(release) >= 4 else (int(year) if year else None)

    return {
        "tmdb_id":         tmdb_id,
        "titulo":          _titulo(details, best, title),
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


def _search_tmdb_tv(title, year, genres_map):
    """Return enriched dict for a TV show or None if not found."""
    data = _tmdb("/search/tv", {"query": title, "first_air_date_year": year, "language": "en-US"})
    results = data.get("results") or []
    if not results:
        data = _tmdb("/search/tv", {"query": title, "language": "en-US"})
        results = data.get("results") or []
    if not results:
        return None

    best = results[0]
    tmdb_id = best["id"]
    details    = _tmdb(f"/tv/{tmdb_id}", {"language": "en-US"})
    details_pt = _tmdb(f"/tv/{tmdb_id}", {"language": "pt-BR"})

    poster_tmdb = details.get("poster_path") or best.get("poster_path")
    poster_local = _download_poster(poster_tmdb) if poster_tmdb else None

    generos = [g["name"] for g in details.get("genres", [])]
    if not generos:
        genre_ids = best.get("genre_ids") or []
        generos = [genres_map[gid] for gid in genre_ids if gid in genres_map]

    air_date = details.get("first_air_date") or best.get("first_air_date") or ""
    ano = int(air_date[:4]) if len(air_date) >= 4 else (int(year) if year else None)

    runtimes = details.get("episode_run_time") or []
    duracao = runtimes[0] if runtimes else None

    orig_lang = details.get("original_language") or best.get("original_language", "en")
    if orig_lang == "pt":
        titulo = details.get("original_name") or best.get("original_name") or title
    else:
        titulo = details.get("name") or best.get("name") or title

    return {
        "tmdb_id":         tmdb_id,
        "titulo":          titulo,
        "titulo_pt":       details_pt.get("name"),
        "titulo_original": details.get("original_name"),
        "ano":             ano,
        "duracao_min":     duracao,
        "genero":          generos,
        "sinopse":         details.get("overview") or best.get("overview"),
        "tagline":         details.get("tagline") or None,
        "nota_tmdb":       details.get("vote_average"),
        "votos_tmdb":      details.get("vote_count"),
        "poster_path":     poster_local,
    }


# ── Provider helpers ─────────────────────────────────────────────────────────

def _download_logo(logo_path_tmdb):
    filename = logo_path_tmdb.lstrip("/")
    local = PROVIDERS_DIR / filename
    if local.exists():
        return f"data/images/providers/{filename}"
    try:
        r = requests.get(f"{TMDB_LOGO}{logo_path_tmdb}", timeout=10)
        r.raise_for_status()
        local.write_bytes(r.content)
        time.sleep(0.05)
        return f"data/images/providers/{filename}"
    except Exception:
        return None


def _fetch_providers_tmdb(tmdb_id):
    """Retorna lista de providers de BR e US para um filme."""
    data = _tmdb(f"/movie/{tmdb_id}/watch/providers")
    results = data.get("results", {})
    providers = []
    seen = set()
    for region in REGIONS:
        region_data = results.get(region, {})
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
                    "logo_path_tmdb":   p.get("logo_path", ""),
                    "tipo":             ptype,
                })
    return providers


def _get_or_create_plataforma(conn, p):
    """Upsert na filmes.plataforma e filmes.plataforma_config, retorna UUID."""
    logo_url  = f"{TMDB_LOGO}{p['logo_path_tmdb']}" if p["logo_path_tmdb"] else None
    try:
        logo_path = _download_logo(p["logo_path_tmdb"]) if p["logo_path_tmdb"] else None
    except Exception:
        logo_path = None

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO filmes.plataforma (nome, tmdb_provider_id, regiao, logo_url, logo_path)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (nome) DO UPDATE SET
                tmdb_provider_id = COALESCE(EXCLUDED.tmdb_provider_id, filmes.plataforma.tmdb_provider_id),
                logo_url         = COALESCE(EXCLUDED.logo_url,         filmes.plataforma.logo_url),
                logo_path        = COALESCE(EXCLUDED.logo_path,        filmes.plataforma.logo_path),
                updated_at       = now()
            RETURNING id
        """, (p["nome"], p["tmdb_provider_id"], p["regiao"], logo_url, logo_path))
        plat_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO filmes.plataforma_config (plataforma_id)
            VALUES (%s)
            ON CONFLICT (plataforma_id) DO NOTHING
        """, (plat_id,))

    return plat_id


def _sync_providers(conn, filme_id, tmdb_id):
    """Sincroniza providers do TMDB para um filme. Retorna contagem."""
    providers = _fetch_providers_tmdb(tmdb_id)
    if not providers:
        return 0

    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM filmes.filme_plataforma WHERE filme_id = %s AND fonte = 'tmdb'",
            (filme_id,),
        )

    count = 0
    for p in providers:
        plat_id = _get_or_create_plataforma(conn, p)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO filmes.filme_plataforma (filme_id, plataforma_id, tipo, fonte)
                VALUES (%s, %s, %s, 'tmdb')
                ON CONFLICT (filme_id, plataforma_id) DO UPDATE SET
                    tipo       = EXCLUDED.tipo,
                    fonte      = 'tmdb',
                    updated_at = now()
            """, (filme_id, plat_id, p["tipo"]))
        count += 1

    return count


# ── CSV helpers ───────────────────────────────────────────────────────────────

def _csv(filename):
    with open(DATA_DIR / filename, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _dt(s):
    """Date string → UTC-aware datetime, or None."""
    if not s or not s.strip():
        return None
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _date(s):
    """Date string → date object, or None."""
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


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()

    print("=" * 60)
    print("  IMPORTACAO LETTERBOXD -> PostgreSQL (filmes)")
    print("=" * 60)
    print(f"  Banco  : {DB_USER}@{DB_HOST}/{DB_NAME}")
    print(f"  Dados  : {DATA_DIR}")
    print(f"  Posters: {POSTERS_DIR}")
    print(f"  TMDB   : {'configurado' if TMDB_KEY else 'SEM CHAVE — metadados omitidos'}")
    print()

    print("Conectando ao banco...", end=" ", flush=True)
    conn = psycopg.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    print("OK")

    # ── 1. Collect unique films ───────────────────────────────────────────────
    films_by_uri: dict[str, dict] = {}
    for source in ("watched.csv", "watchlist.csv"):
        for row in _csv(source):
            uri = row["Letterboxd URI"].strip()
            if uri not in films_by_uri:
                films_by_uri[uri] = {
                    "name": row["Name"].strip(),
                    "year": row["Year"].strip(),
                }

    total = len(films_by_uri)
    print(f"\nFilmes únicos encontrados nos CSVs: {total}")

    if TMDB_KEY:
        print("Carregando lista de gêneros do TMDB...", end=" ", flush=True)
        genres_map = _load_genres()
        print(f"OK ({len(genres_map)} gêneros)")
    else:
        genres_map = {}

    # ── 2. Upsert films ───────────────────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print(f"  FASE 1/5 — Filmes ({total} itens)")
    print(f"{'─' * 60}")

    uri_to_id: dict[str, object] = {}
    tmdb_hits = tmdb_misses = posters_novos = posters_cache = 0

    for i, (uri, info) in enumerate(films_by_uri.items(), 1):
        name, year = info["name"], info["year"]
        pct = i * 100 // total

        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM filmes.filme WHERE letterboxd_uri = %s AND tmdb_id IS NOT NULL",
                (uri,),
            )
            row = cur.fetchone()
        if row:
            uri_to_id[uri] = row[0]
            print(f"[{i:>3}/{total}  {pct:>3}%] {name} ({year}) — ja preenchido, pulando")
            continue

        print(f"[{i:>3}/{total}  {pct:>3}%] {name} ({year})", end="")

        tmdb = None
        if TMDB_KEY:
            try:
                tmdb = _search_tmdb(name, year, genres_map)
            except Exception as e:
                print(f"\n          TMDB erro: {e}", end="")

        if tmdb and tmdb["tmdb_id"]:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM filmes.filme WHERE tmdb_id = %s AND letterboxd_uri != %s",
                    (tmdb["tmdb_id"], uri),
                )
                if cur.fetchone():
                    print("\n          tmdb_id duplicado, tentando busca de serie...", end="")
                    try:
                        tmdb = _search_tmdb_tv(name, year, genres_map)
                    except Exception as e:
                        print(f" erro: {e}", end="")
                        tmdb = None

        if tmdb:
            tmdb_hits += 1
            duracao = f"{tmdb['duracao_min']} min" if tmdb["duracao_min"] else "duração ?"
            generos_str = ", ".join(tmdb["genero"][:3]) if tmdb["genero"] else "sem gênero"
            nota_str = f"{tmdb['nota_tmdb']:.1f}" if tmdb["nota_tmdb"] else "s/nota"
            poster_status = ""
            if tmdb["poster_path"]:
                poster_status = " [poster: baixado]"
                posters_novos += 1
            else:
                poster_status = " [poster: nenhum]"
            print(f"\n          TMDB #{tmdb['tmdb_id']} | {duracao} | {generos_str} | nota {nota_str}{poster_status}", end="")
            vals = (
                tmdb["titulo"] or name,
                tmdb.get("titulo_pt"),
                tmdb["titulo_original"],
                tmdb["ano"] or (int(year) if year else None),
                tmdb["duracao_min"],
                tmdb["genero"],
                tmdb["tmdb_id"],
                uri,
                tmdb["sinopse"],
                tmdb["tagline"],
                tmdb["nota_tmdb"],
                tmdb["votos_tmdb"],
                tmdb["poster_path"],
            )
        else:
            if TMDB_KEY:
                tmdb_misses += 1
                print("\n          TMDB: nao encontrado", end="")
            vals = (
                name, None, None,
                int(year) if year else None,
                None, [],
                None, uri,
                None, None, None, None, None,
            )

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO filmes.filme
                    (titulo, titulo_pt, titulo_original, ano, duracao_min, genero,
                     tmdb_id, letterboxd_uri, sinopse, tagline,
                     nota_tmdb, votos_tmdb, poster_path)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (letterboxd_uri) DO UPDATE SET
                    titulo          = EXCLUDED.titulo,
                    titulo_pt       = EXCLUDED.titulo_pt,
                    titulo_original = EXCLUDED.titulo_original,
                    ano             = EXCLUDED.ano,
                    duracao_min     = EXCLUDED.duracao_min,
                    genero          = EXCLUDED.genero,
                    tmdb_id         = EXCLUDED.tmdb_id,
                    sinopse         = EXCLUDED.sinopse,
                    tagline         = EXCLUDED.tagline,
                    nota_tmdb       = EXCLUDED.nota_tmdb,
                    votos_tmdb      = EXCLUDED.votos_tmdb,
                    poster_path     = EXCLUDED.poster_path,
                    updated_at      = now()
                RETURNING id
            """, vals)
            film_id = cur.fetchone()[0]

        conn.commit()
        uri_to_id[uri] = film_id
        print()

    print(f"\n  Filmes inseridos/atualizados : {total}")
    if TMDB_KEY:
        print(f"  TMDB encontrados            : {tmdb_hits}")
        print(f"  TMDB nao encontrados        : {tmdb_misses}")
        print(f"  Posters baixados agora      : {posters_novos}")
        print(f"  Posters do cache            : {posters_cache}")

    # ── 3. Avaliações ─────────────────────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print(f"  FASE 2/5 — Avaliacoes")
    print(f"{'─' * 60}")
    n = sem_filme = 0
    for row in _csv("ratings.csv"):
        uri = row["Letterboxd URI"].strip()
        film_id = uri_to_id.get(uri)
        nota = _rating(row.get("Rating"))
        if not film_id:
            sem_filme += 1
            continue
        if nota is None:
            continue
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO filmes.avaliacao (filme_id, nota, avaliado_em)
                VALUES (%s, %s, %s)
                ON CONFLICT (filme_id) DO UPDATE SET
                    nota        = EXCLUDED.nota,
                    avaliado_em = EXCLUDED.avaliado_em,
                    updated_at  = now()
            """, (film_id, nota, _dt(row["Date"])))
        conn.commit()
        n += 1
        print(f"  {row['Name'][:45]:<45} -> {nota} estrelas")
    print(f"\n  Total: {n} avaliacoes inseridas")
    if sem_filme:
        print(f"  Ignorados (filme nao mapeado): {sem_filme}")

    # ── 4. Diário ─────────────────────────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print(f"  FASE 3/5 — Diario")
    print(f"{'─' * 60}")
    n = 0
    for row in _csv("diary.csv"):
        uri = row["Letterboxd URI"].strip()
        film_id = uri_to_id.get(uri)
        if not film_id:
            continue
        tags_raw = row.get("Tags", "").strip()
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] or None
        rewatch = row.get("Rewatch", "").strip().lower() == "yes"
        watched = row.get("Watched Date", "").strip() or "?"
        nota = _rating(row.get("Rating"))
        nota_str = f"{nota}" if nota else "-"
        rewatch_str = " [rewatch]" if rewatch else ""
        print(f"  {row['Name'][:40]:<40} assistido {watched}  nota {nota_str}{rewatch_str}")
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO filmes.diario
                    (filme_id, assistido_em, rewatch, tags, nota, avaliado_em)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (filme_id, avaliado_em) DO NOTHING
            """, (
                film_id,
                _date(row.get("Watched Date")),
                rewatch,
                tags,
                nota,
                _dt(row["Date"]),
            ))
        conn.commit()
        n += 1
    print(f"\n  Total: {n} entradas inseridas")

    # ── 5. Reviews ────────────────────────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print(f"  FASE 4/5 — Reviews")
    print(f"{'─' * 60}")
    n = 0
    for row in _csv("reviews.csv"):
        uri = row["Letterboxd URI"].strip()
        film_id = uri_to_id.get(uri)
        texto = row.get("Review", "").strip()
        if not film_id or not texto:
            continue
        preview = texto[:60].replace("\n", " ")
        print(f"  {row['Name'][:35]:<35} \"{preview}...\"")
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO filmes.review
                    (filme_id, texto, nota, rewatch, assistido_em, avaliado_em)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (filme_id) DO UPDATE SET
                    texto        = EXCLUDED.texto,
                    nota         = EXCLUDED.nota,
                    rewatch      = EXCLUDED.rewatch,
                    assistido_em = EXCLUDED.assistido_em,
                    avaliado_em  = EXCLUDED.avaliado_em,
                    updated_at   = now()
            """, (
                film_id,
                texto,
                _rating(row.get("Rating")),
                row.get("Rewatch", "").strip().lower() == "yes",
                _date(row.get("Watched Date")),
                _dt(row["Date"]),
            ))
        conn.commit()
        n += 1
    print(f"\n  Total: {n} reviews inseridas")

    # ── 6. Watch log ──────────────────────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print(f"  FASE 5/7 — Watch log (diary + watched)")
    print(f"{'─' * 60}")

    # Constrói mapa URI -> melhor data do diary.csv
    # Filmes só em watched.csv (sem entrada no diary) não têm data confiável:
    # o "Date" do watched é a data do log, não a data de assistido.
    diary_dates: dict[str, str] = {}   # URI -> data a usar
    diary_has_wd: set[str]      = set()  # URIs com "Watched Date" explícita
    for row in _csv("diary.csv"):
        uri = row["Letterboxd URI"].strip()
        wd  = row.get("Watched Date", "").strip()
        dt  = row.get("Date", "").strip()
        if uri in diary_dates:
            continue
        if wd:
            diary_dates[uri] = wd
            diary_has_wd.add(uri)
        elif dt:
            diary_dates[uri] = dt

    n_wlog = 0
    for row in _csv("watched.csv"):
        uri     = row["Letterboxd URI"].strip()
        film_id = uri_to_id.get(uri)
        if not film_id:
            continue
        # Só cria watch_log se houver entrada no diary; caso contrário não há
        # data confiável (o "Date" do watched.csv é apenas a data do log).
        date_str = diary_dates.get(uri)
        if not date_str:
            continue
        ocorrido_em = _dt(date_str)
        if not ocorrido_em:
            continue
        source = "diary-wd" if uri in diary_has_wd else "diary-date"
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO filmes.watch_log (filme_id, ocorrido_em, data_precisao)
                VALUES (%s, %s, 'dia')
                ON CONFLICT DO NOTHING
            """, (film_id, ocorrido_em))
        conn.commit()
        n_wlog += 1
        print(f"  {row['Name'][:45]:<45} {date_str}  [{source}]")
    print(f"\n  {n_wlog} entradas inseridas")

    # ── 7. Providers TMDB ─────────────────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print(f"  FASE 6/7 — Providers TMDB")
    print(f"{'─' * 60}")
    n_prov = n_prov_filmes = 0
    if TMDB_KEY:
        for uri, film_id in uri_to_id.items():
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT tmdb_id, titulo FROM filmes.filme WHERE id = %s AND tmdb_id IS NOT NULL",
                    (film_id,),
                )
                row = cur.fetchone()
            if not row:
                continue
            tmdb_id, titulo = row
            print(f"  {titulo[:50]:<50}", end=" ", flush=True)
            try:
                count = _sync_providers(conn, film_id, tmdb_id)
                conn.commit()
                print(f"{count} providers")
                if count:
                    n_prov += count
                    n_prov_filmes += 1
            except Exception as e:
                conn.rollback()
                print(f"erro: {e}")
        print(f"\n  {n_prov_filmes} filmes com providers ({n_prov} vínculos)")
    else:
        print("  TMDB_API_KEY ausente, pulando")

    # ── 8. Watchlist + Curtidas ───────────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print(f"  FASE 7/7 — Watchlist e Curtidas")
    print(f"{'─' * 60}")

    n_wl = 0
    for row in _csv("watchlist.csv"):
        uri = row["Letterboxd URI"].strip()
        film_id = uri_to_id.get(uri)
        if not film_id:
            continue
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO filmes.watchlist (filme_id, adicionado_em)
                VALUES (%s, %s)
                ON CONFLICT (filme_id) DO NOTHING
            """, (film_id, _dt(row["Date"])))
        conn.commit()
        n_wl += 1

    n_ct = 0
    for row in _csv("likes/films.csv"):
        uri = row["Letterboxd URI"].strip()
        film_id = uri_to_id.get(uri)
        if not film_id:
            continue
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO filmes.curtida (filme_id, curtido_em)
                VALUES (%s, %s)
                ON CONFLICT (filme_id) DO NOTHING
            """, (film_id, _dt(row["Date"])))
        conn.commit()
        n_ct += 1

    print(f"  Watchlist : {n_wl} filmes inseridos")
    print(f"  Curtidas  : {n_ct} filmes inseridos")

    # ── Resumo final ──────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    conn.close()
    print(f"\n{'=' * 60}")
    print(f"  CONCLUIDO em {elapsed:.0f}s")
    print(f"{'=' * 60}")
    print(f"  Filmes    : {total}")
    print(f"  Avaliacoes: {n}")
    print(f"  Watch log : {n_wlog}")
    print(f"  Providers : {n_prov} vinculos em {n_prov_filmes} filmes")
    print(f"  Watchlist : {n_wl}")
    print(f"  Curtidas  : {n_ct}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
