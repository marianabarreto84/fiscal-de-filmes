import sqlite3

DB_PATH = "filmes.db"

_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS lists (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    url         TEXT UNIQUE NOT NULL,
    name        TEXT,
    owner       TEXT,
    description TEXT,
    film_count  INTEGER,
    scraped_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS films (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    letterboxd_slug TEXT UNIQUE NOT NULL,
    letterboxd_url  TEXT,
    title           TEXT,
    original_title  TEXT,
    year            INTEGER,
    runtime         INTEGER,
    synopsis        TEXT,
    tagline         TEXT,
    average_rating  REAL,
    ratings_count   INTEGER,
    watches_count   INTEGER,
    likes_count     INTEGER,
    scraped_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS list_films (
    list_id  INTEGER NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
    film_id  INTEGER NOT NULL REFERENCES films(id) ON DELETE CASCADE,
    position INTEGER,
    notes    TEXT,
    PRIMARY KEY (list_id, film_id)
);

CREATE TABLE IF NOT EXISTS people (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    letterboxd_slug TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS film_cast (
    film_id   INTEGER NOT NULL REFERENCES films(id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL REFERENCES people(id),
    position  INTEGER,
    PRIMARY KEY (film_id, person_id)
);

CREATE TABLE IF NOT EXISTS film_crew (
    film_id   INTEGER NOT NULL REFERENCES films(id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL REFERENCES people(id),
    role      TEXT NOT NULL,
    PRIMARY KEY (film_id, person_id, role)
);

CREATE TABLE IF NOT EXISTS genres (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS film_genres (
    film_id  INTEGER NOT NULL REFERENCES films(id) ON DELETE CASCADE,
    genre_id INTEGER NOT NULL REFERENCES genres(id),
    PRIMARY KEY (film_id, genre_id)
);

CREATE TABLE IF NOT EXISTS themes (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS film_themes (
    film_id  INTEGER NOT NULL REFERENCES films(id) ON DELETE CASCADE,
    theme_id INTEGER NOT NULL REFERENCES themes(id),
    PRIMARY KEY (film_id, theme_id)
);

CREATE TABLE IF NOT EXISTS countries (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS film_countries (
    film_id    INTEGER NOT NULL REFERENCES films(id) ON DELETE CASCADE,
    country_id INTEGER NOT NULL REFERENCES countries(id),
    PRIMARY KEY (film_id, country_id)
);

CREATE TABLE IF NOT EXISTS languages (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS film_languages (
    film_id     INTEGER NOT NULL REFERENCES films(id) ON DELETE CASCADE,
    language_id INTEGER NOT NULL REFERENCES languages(id),
    PRIMARY KEY (film_id, language_id)
);

CREATE TABLE IF NOT EXISTS studios (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS film_studios (
    film_id   INTEGER NOT NULL REFERENCES films(id) ON DELETE CASCADE,
    studio_id INTEGER NOT NULL REFERENCES studios(id),
    PRIMARY KEY (film_id, studio_id)
);
"""


def connect(path=None):
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn):
    conn.executescript(_SCHEMA)
    conn.commit()


def upsert_film(conn, data):
    conn.execute(
        """
        INSERT INTO films (
            letterboxd_slug, letterboxd_url, title, original_title,
            year, runtime, synopsis, tagline,
            average_rating, ratings_count, watches_count, likes_count
        ) VALUES (
            :letterboxd_slug, :letterboxd_url, :title, :original_title,
            :year, :runtime, :synopsis, :tagline,
            :average_rating, :ratings_count, :watches_count, :likes_count
        )
        ON CONFLICT(letterboxd_slug) DO UPDATE SET
            title          = excluded.title,
            original_title = excluded.original_title,
            year           = excluded.year,
            runtime        = excluded.runtime,
            synopsis       = excluded.synopsis,
            tagline        = excluded.tagline,
            average_rating = excluded.average_rating,
            ratings_count  = excluded.ratings_count,
            watches_count  = excluded.watches_count,
            likes_count    = excluded.likes_count,
            scraped_at     = datetime('now')
        """,
        data,
    )
    return conn.execute(
        "SELECT id FROM films WHERE letterboxd_slug = ?",
        (data["letterboxd_slug"],),
    ).fetchone()["id"]


def _get_or_create_person(conn, name, slug=None):
    if slug:
        conn.execute(
            "INSERT OR IGNORE INTO people (name, letterboxd_slug) VALUES (?, ?)",
            (name, slug),
        )
        row = conn.execute(
            "SELECT id FROM people WHERE letterboxd_slug = ?", (slug,)
        ).fetchone()
    else:
        conn.execute("INSERT OR IGNORE INTO people (name) VALUES (?)", (name,))
        row = conn.execute(
            "SELECT id FROM people WHERE name = ? AND letterboxd_slug IS NULL", (name,)
        ).fetchone()
    return row["id"] if row else None


def _get_or_create(conn, table, name):
    conn.execute(f"INSERT OR IGNORE INTO {table} (name) VALUES (?)", (name,))
    return conn.execute(
        f"SELECT id FROM {table} WHERE name = ?", (name,)
    ).fetchone()["id"]


def save_film_relations(conn, film_id, film_data):
    for i, person in enumerate(film_data.get("cast", [])):
        pid = _get_or_create_person(conn, person["name"], person.get("slug"))
        if pid:
            conn.execute(
                "INSERT OR IGNORE INTO film_cast (film_id, person_id, position) VALUES (?, ?, ?)",
                (film_id, pid, i),
            )

    for role, people in film_data.get("crew", {}).items():
        for person in people:
            pid = _get_or_create_person(conn, person["name"], person.get("slug"))
            if pid:
                conn.execute(
                    "INSERT OR IGNORE INTO film_crew (film_id, person_id, role) VALUES (?, ?, ?)",
                    (film_id, pid, role),
                )

    for name in film_data.get("genres", []):
        gid = _get_or_create(conn, "genres", name)
        conn.execute(
            "INSERT OR IGNORE INTO film_genres (film_id, genre_id) VALUES (?, ?)",
            (film_id, gid),
        )

    for name in film_data.get("themes", []):
        tid = _get_or_create(conn, "themes", name)
        conn.execute(
            "INSERT OR IGNORE INTO film_themes (film_id, theme_id) VALUES (?, ?)",
            (film_id, tid),
        )

    for name in film_data.get("countries", []):
        cid = _get_or_create(conn, "countries", name)
        conn.execute(
            "INSERT OR IGNORE INTO film_countries (film_id, country_id) VALUES (?, ?)",
            (film_id, cid),
        )

    for name in film_data.get("languages", []):
        lid = _get_or_create(conn, "languages", name)
        conn.execute(
            "INSERT OR IGNORE INTO film_languages (film_id, language_id) VALUES (?, ?)",
            (film_id, lid),
        )

    for name in film_data.get("studios", []):
        sid = _get_or_create(conn, "studios", name)
        conn.execute(
            "INSERT OR IGNORE INTO film_studios (film_id, studio_id) VALUES (?, ?)",
            (film_id, sid),
        )


def save_list(conn, url, meta):
    conn.execute(
        """
        INSERT INTO lists (url, name, owner, description, film_count)
        VALUES (:url, :name, :owner, :description, :film_count)
        ON CONFLICT(url) DO UPDATE SET
            name       = excluded.name,
            film_count = excluded.film_count,
            scraped_at = datetime('now')
        """,
        {"url": url, **meta},
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM lists WHERE url = ?", (url,)
    ).fetchone()["id"]


def is_scraped(conn, slug):
    return conn.execute(
        "SELECT 1 FROM films WHERE letterboxd_slug = ? AND title IS NOT NULL",
        (slug,),
    ).fetchone() is not None
