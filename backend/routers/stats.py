from fastapi import APIRouter
from backend.database import get_db, dict_cursor
from datetime import datetime, date, timedelta
import calendar

router = APIRouter()


@router.get("/overview")
def get_overview():
    conn = get_db()
    try:
        today = date.today()
        week_start = today - timedelta(days=(today.weekday()) % 7)

        with dict_cursor(conn) as cur:
            cur.execute("""
                SELECT COUNT(DISTINCT f.id) AS n FROM filme f
                WHERE EXISTS (SELECT 1 FROM diario d WHERE d.filme_id = f.id)
            """)
            total_filmes = cur.fetchone()["n"]

            cur.execute("""
                SELECT COUNT(*) AS n FROM diario
            """)
            total_watched = cur.fetchone()["n"]

            cur.execute("""
                SELECT COALESCE(SUM(f.duracao_min), 0) AS n
                FROM diario d
                JOIN filme f ON f.id = d.filme_id
            """)
            minutes_watched = cur.fetchone()["n"] or 0

            cur.execute("""
                SELECT COUNT(*) AS n FROM diario
                WHERE EXTRACT(YEAR  FROM assistido_em) = %s
                  AND EXTRACT(MONTH FROM assistido_em) = %s
                  AND EXTRACT(DAY   FROM assistido_em) = %s
            """, (today.year, today.month, today.day))
            today_count = cur.fetchone()["n"]

            cur.execute("""
                SELECT COUNT(*) AS n FROM diario
                WHERE assistido_em BETWEEN %s AND %s
            """, (week_start.isoformat(), today.isoformat()))
            week_count = cur.fetchone()["n"]

            cur.execute("""
                SELECT COUNT(*) AS n FROM diario
                WHERE EXTRACT(YEAR  FROM assistido_em) = %s
                  AND EXTRACT(MONTH FROM assistido_em) = %s
            """, (today.year, today.month))
            month_count = cur.fetchone()["n"]

            cur.execute("""
                SELECT COUNT(*) AS n FROM diario
                WHERE EXTRACT(YEAR FROM assistido_em) = %s
            """, (today.year,))
            year_count = cur.fetchone()["n"]

            last_week_start = week_start - timedelta(days=7)
            last_week_end   = week_start - timedelta(days=1)
            last_month      = (today.replace(day=1) - timedelta(days=1))

            cur.execute("""
                SELECT COUNT(*) AS n FROM diario
                WHERE assistido_em BETWEEN %s AND %s
            """, (last_week_start.isoformat(), last_week_end.isoformat()))
            last_week_count = cur.fetchone()["n"]

            cur.execute("""
                SELECT COUNT(*) AS n FROM diario
                WHERE EXTRACT(YEAR  FROM assistido_em) = %s
                  AND EXTRACT(MONTH FROM assistido_em) = %s
            """, (last_month.year, last_month.month))
            last_month_count = cur.fetchone()["n"]

            cur.execute("""
                SELECT COUNT(*) AS n FROM diario
                WHERE EXTRACT(YEAR FROM assistido_em) = %s
            """, (today.year - 1,))
            last_year_count = cur.fetchone()["n"]

        days_into_week  = (today - week_start).days + 1
        days_into_month = today.day
        days_into_year  = (today - today.replace(month=1, day=1)).days + 1
        days_in_month   = calendar.monthrange(today.year, today.month)[1]
        days_in_year    = 366 if calendar.isleap(today.year) else 365

        return {
            "total_filmes":         total_filmes,
            "total_watched":        total_watched,
            "total_minutes_watched": minutes_watched,
            "total_hours_watched":  round(minutes_watched / 60, 1),
            "today":                today_count,
            "this_week":            week_count,
            "this_month":           month_count,
            "this_year":            year_count,
            "last_week":            last_week_count,
            "last_month":           last_month_count,
            "last_year":            last_year_count,
            "days_into_week":       days_into_week,
            "days_into_month":      days_into_month,
            "days_into_year":       days_into_year,
            "days_in_month":        days_in_month,
            "days_in_year":         days_in_year,
        }
    finally:
        conn.close()


@router.get("/by-month")
def get_by_month(year: int = None):
    conn = get_db()
    try:
        if not year:
            year = date.today().year
        with dict_cursor(conn) as cur:
            cur.execute("""
                SELECT EXTRACT(MONTH FROM assistido_em)::int AS mes,
                       COUNT(*) AS filmes,
                       COALESCE(SUM(f.duracao_min), 0) AS minutos
                FROM diario d
                JOIN filme f ON f.id = d.filme_id
                WHERE EXTRACT(YEAR FROM assistido_em) = %s
                  AND assistido_em IS NOT NULL
                GROUP BY mes
                ORDER BY mes
            """, (year,))
            rows = cur.fetchall()

        months = {i: {"mes": i, "filmes": 0, "minutos": 0} for i in range(1, 13)}
        for r in rows:
            months[r["mes"]] = {"mes": r["mes"], "filmes": r["filmes"], "minutos": r["minutos"]}
        return list(months.values())
    finally:
        conn.close()


@router.get("/by-year")
def get_by_year():
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("""
                SELECT EXTRACT(YEAR FROM assistido_em)::int AS ano,
                       COUNT(*) AS filmes,
                       COALESCE(SUM(f.duracao_min), 0) AS minutos
                FROM diario d
                JOIN filme f ON f.id = d.filme_id
                WHERE assistido_em IS NOT NULL
                GROUP BY ano
                ORDER BY ano
            """)
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/by-day-of-week")
def get_by_day_of_week():
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("""
                SELECT COUNT(*) AS filmes,
                       EXTRACT(DOW FROM assistido_em)::int AS dow
                FROM diario
                WHERE assistido_em IS NOT NULL
                GROUP BY dow
            """)
            rows = cur.fetchall()

        day_counts = {i: 0 for i in range(7)}
        for r in rows:
            day_counts[r["dow"]] += r["filmes"]

        days = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
        return [{"dia": days[i], "filmes": day_counts[i]} for i in range(7)]
    finally:
        conn.close()


@router.get("/top-filmes")
def get_top_filmes(limit: int = 10):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("""
                SELECT f.titulo, f.poster_path,
                       COUNT(d.id) AS vezes_assistido,
                       COALESCE(SUM(f.duracao_min), 0) AS minutos_totais
                FROM filme f
                JOIN diario d ON d.filme_id = f.id
                GROUP BY f.id
                ORDER BY vezes_assistido DESC
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/recent")
def get_recent(limit: int = 20):
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("""
                SELECT d.*, f.titulo AS filme_titulo, f.poster_path, f.duracao_min
                FROM diario d
                JOIN filme f ON f.id = d.filme_id
                ORDER BY d.assistido_em DESC NULLS LAST, d.id DESC
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/available-years")
def get_available_years():
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("""
                SELECT DISTINCT EXTRACT(YEAR FROM assistido_em)::int AS ano
                FROM diario
                WHERE assistido_em IS NOT NULL
                ORDER BY ano DESC
            """)
            rows = cur.fetchall()
        return [r["ano"] for r in rows]
    finally:
        conn.close()
