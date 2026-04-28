"""
Re-baixa os posters de todos os filmes do banco usando o idioma correto:
  - Filmes nacionais (original_language == 'pt'): poster em pt-BR
  - Demais filmes: poster em inglês via /movie/{id}/images?include_image_language=en

Uso: poetry run python update_posters.py [--dry-run] [--force]

  --dry-run  Mostra o que faria sem baixar ou alterar nada.
  --force    Re-baixa mesmo que o arquivo já exista localmente.
"""
import argparse
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

TMDB_BASE   = "https://api.themoviedb.org/3"
TMDB_IMG_W  = "https://image.tmdb.org/t/p/w500"
POSTERS_DIR = Path(__file__).parent / "data" / "images" / "posters"
POSTERS_DIR.mkdir(parents=True, exist_ok=True)


def tmdb(path, params=None):
    r = requests.get(
        f"{TMDB_BASE}{path}",
        params={"api_key": TMDB_KEY, **(params or {})},
        timeout=10,
    )
    r.raise_for_status()
    time.sleep(0.12)
    return r.json()


def download_poster(poster_path_tmdb, force=False):
    """Baixa poster do TMDB para local; retorna caminho relativo ou None."""
    filename = poster_path_tmdb.lstrip("/")
    local = POSTERS_DIR / filename
    if local.exists() and not force:
        return f"data/images/posters/{filename}"
    try:
        r = requests.get(f"{TMDB_IMG_W}/{filename}", timeout=15)
        r.raise_for_status()
        local.write_bytes(r.content)
        time.sleep(0.12)
        return f"data/images/posters/{filename}"
    except Exception as e:
        print(f"    ! Erro ao baixar {filename}: {e}")
        return None


def best_english_poster(tmdb_id):
    """
    Retorna o poster_path do melhor poster em inglês (vote_count mais alto).
    Usa /movie/{id}/images?include_image_language=en para filtragem explícita.
    Fallback: poster do /movie/{id}?language=en-US.
    """
    try:
        data = tmdb(f"/movie/{tmdb_id}/images", {
            "include_image_language": "en,null"
        })
        posters = data.get("posters", [])
        if posters:
            # Prefere o poster com mais votos (mais popular)
            best = max(posters, key=lambda p: p.get("vote_count", 0))
            return best["file_path"]
    except Exception:
        pass

    # Fallback: endpoint principal com en-US
    try:
        data = tmdb(f"/movie/{tmdb_id}", {"language": "en-US"})
        return data.get("poster_path")
    except Exception:
        return None


def best_pt_poster(tmdb_id):
    """
    Retorna o poster_path em pt-BR para filmes nacionais.
    Fallback: poster do /movie/{id}?language=pt-BR; se ausente, usa en-US.
    """
    try:
        data = tmdb(f"/movie/{tmdb_id}/images", {
            "include_image_language": "pt,null"
        })
        posters = data.get("posters", [])
        if posters:
            best = max(posters, key=lambda p: p.get("vote_count", 0))
            return best["file_path"]
    except Exception:
        pass

    try:
        data = tmdb(f"/movie/{tmdb_id}", {"language": "pt-BR"})
        return data.get("poster_path")
    except Exception:
        return None


def get_original_language(tmdb_id):
    try:
        data = tmdb(f"/movie/{tmdb_id}", {"language": "en-US"})
        return data.get("original_language", "")
    except Exception:
        return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force",   action="store_true", help="Re-baixa mesmo que já exista")
    args = parser.parse_args()

    if not TMDB_KEY:
        print("TMDB_API_KEY não configurada no .env")
        return

    conn = psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT id, titulo, tmdb_id, poster_path
        FROM filmes.filme
        WHERE tmdb_id IS NOT NULL
        ORDER BY titulo
    """)
    filmes = cur.fetchall()
    total = len(filmes)

    print(f"{'[DRY-RUN] ' if args.dry_run else ''}Processando {total} filmes...\n")

    atualizados = erros = pulados = nacionais = 0

    for i, f in enumerate(filmes, 1):
        tmdb_id   = f["tmdb_id"]
        titulo    = f["titulo"]
        filme_id  = f["id"]
        pct       = i * 100 // total
        prefix    = f"[{i:>4}/{total}  {pct:>3}%]"

        print(f"{prefix} {titulo[:50]}", end=" ", flush=True)

        orig_lang = get_original_language(tmdb_id)
        nacional  = (orig_lang == "pt")

        if nacional:
            nacionais += 1
            poster_path = best_pt_poster(tmdb_id)
            tag = "[PT]"
        else:
            poster_path = best_english_poster(tmdb_id)
            tag = "[EN]"

        if not poster_path:
            print(f"-> sem poster TMDB")
            erros += 1
            continue

        filename  = poster_path.lstrip("/")
        local_rel = f"data/images/posters/{filename}"
        local_abs = POSTERS_DIR / filename

        same = (f["poster_path"] and f["poster_path"].replace("\\", "/") == local_rel)

        if same and local_abs.exists() and not args.force:
            print(f"-> ok {tag}")
            pulados += 1
            continue

        if args.dry_run:
            print(f"-> ATUALIZARIA {tag} {filename[:30]}")
            atualizados += 1
            continue

        local_path = download_poster(poster_path, force=args.force)
        if not local_path:
            erros += 1
            continue

        cur.execute(
            "UPDATE filmes.filme SET poster_path = %s, updated_at = now() WHERE id = %s",
            (local_path, filme_id),
        )
        conn.commit()
        print(f"-> baixado {tag} {filename[:30]}")
        atualizados += 1

    cur.close()
    conn.close()

    print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}Concluído:")
    print(f"  Atualizados : {atualizados}")
    print(f"  Já corretos : {pulados}")
    print(f"  Nacionais   : {nacionais}")
    print(f"  Erros       : {erros}")


if __name__ == "__main__":
    main()
