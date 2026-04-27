import argparse
import sys

import db
import letterboxd


def main():
    parser = argparse.ArgumentParser(
        description="Scrape a Letterboxd list and save everything to SQLite."
    )
    parser.add_argument("list_url", help="URL da lista no Letterboxd")
    parser.add_argument(
        "--db", default=db.DB_PATH, metavar="PATH",
        help="Caminho do banco SQLite (padrão: filmes.db)"
    )
    parser.add_argument(
        "--delay", type=float, default=letterboxd.DELAY, metavar="SECS",
        help="Pausa entre requests em segundos (padrão: 1.5)"
    )
    parser.add_argument(
        "--skip-scraped", action="store_true",
        help="Pula filmes que já estão no banco com dados completos"
    )
    args = parser.parse_args()

    letterboxd.DELAY = args.delay

    conn = db.connect(args.db)
    db.init_db(conn)

    session = letterboxd.make_session()

    print(f"Buscando lista: {args.list_url}")
    try:
        meta, stubs = letterboxd.scrape_list(session, args.list_url)
    except Exception as e:
        print(f"Erro ao buscar lista: {e}", file=sys.stderr)
        sys.exit(1)

    list_id = db.save_list(conn, args.list_url, meta)
    owner = meta.get("owner") or "?"
    print(f"Lista: \"{meta.get('name') or '?'}\" por {owner} — {len(stubs)} filmes\n")

    ok = skipped = errors = 0

    for stub in stubs:
        slug = stub["slug"]
        title = stub["title"] or slug
        prefix = f"[{stub['position']}/{len(stubs)}]"

        if args.skip_scraped and db.is_scraped(conn, slug):
            print(f"{prefix} Pulando '{title}' (já salvo)")
            skipped += 1
            continue

        print(f"{prefix} '{title}'...", end=" ", flush=True)
        try:
            film_data = letterboxd.scrape_film(session, slug)
            film_id = db.upsert_film(conn, film_data)
            db.save_film_relations(conn, film_id, film_data)
            conn.execute(
                "INSERT OR IGNORE INTO list_films (list_id, film_id, position, notes) "
                "VALUES (?, ?, ?, ?)",
                (list_id, film_id, stub["position"], stub["notes"]),
            )
            conn.commit()

            year = film_data.get("year") or "?"
            rating = film_data.get("average_rating")
            rating_str = f"★{rating:.2f}" if rating else "sem nota"
            print(f"OK  ({year}, {rating_str})")
            ok += 1
        except Exception as e:
            print(f"ERRO: {e}")
            conn.rollback()
            errors += 1

    conn.close()
    print(f"\nConcluído → {ok} salvos, {skipped} pulados, {errors} erros")
    print(f"Banco: {args.db}")


if __name__ == "__main__":
    main()
