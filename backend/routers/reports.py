from fastapi import APIRouter, HTTPException
from backend.database import get_db, dict_cursor
import datetime

router = APIRouter()

PT_MONTHS = [
    '', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
]


def _fetch_report_data(conn, period_filter: str, params: tuple) -> dict:
    with dict_cursor(conn) as cur:
        cur.execute(f"""
            SELECT COUNT(*) AS total_filmes,
                   COALESCE(SUM(f.duracao_min), 0) AS total_minutos
            FROM diario d
            JOIN filme f ON f.id = d.filme_id
            WHERE {period_filter}
        """, params)
        row = cur.fetchone()

    total_filmes  = row["total_filmes"]
    total_minutos = int(row["total_minutos"])

    with dict_cursor(conn) as cur:
        cur.execute(f"""
            SELECT f.id AS filme_id, f.titulo, f.poster_path,
                   COUNT(d.id) AS vezes
            FROM diario d
            JOIN filme f ON f.id = d.filme_id
            WHERE {period_filter}
            GROUP BY f.id
            ORDER BY vezes DESC
            LIMIT 25
        """, params)
        top_filmes = cur.fetchall()

    with dict_cursor(conn) as cur:
        cur.execute(f"""
            SELECT p.id, p.nome, p.logo_path, p.logo_url,
                   COUNT(d.id) AS vezes
            FROM diario d
            JOIN plataforma p ON p.id = d.plataforma_id
            WHERE d.plataforma_id IS NOT NULL
              AND {period_filter}
            GROUP BY p.id
            ORDER BY vezes DESC
            LIMIT 10
        """, params)
        top_plataformas = cur.fetchall()

    return {
        "total_filmes":    total_filmes,
        "total_minutos":   total_minutos,
        "top_filmes":      [dict(r) for r in top_filmes],
        "top_plataformas": [dict(r) for r in top_plataformas],
    }


@router.get("/daily/{date}")
def get_daily_report(date: str):
    try:
        d = datetime.date.fromisoformat(date)
    except ValueError:
        raise HTTPException(400, "Data inválida. Use YYYY-MM-DD.")

    conn = get_db()
    try:
        period_filter = (
            "EXTRACT(YEAR FROM d.assistido_em) = %s "
            "AND EXTRACT(MONTH FROM d.assistido_em) = %s "
            "AND EXTRACT(DAY FROM d.assistido_em) = %s"
        )
        data = _fetch_report_data(conn, period_filter, (d.year, d.month, d.day))
    finally:
        conn.close()

    label = f"{d.day:02d} de {PT_MONTHS[d.month]} de {d.year}"
    return {
        "period_type": "daily",
        "label":       label,
        "date_range":  {"from": date, "to": date},
        **data,
    }


@router.get("/weekly/{year}/{week}")
def get_weekly_report(year: int, week: int):
    try:
        week_start = datetime.date.fromisocalendar(year, week, 1)
        week_end   = datetime.date.fromisocalendar(year, week, 7)
    except ValueError:
        raise HTTPException(400, "Semana inválida.")

    conn = get_db()
    try:
        period_filter = "d.assistido_em BETWEEN %s AND %s"
        data = _fetch_report_data(conn, period_filter,
                                  (week_start.isoformat(), week_end.isoformat()))
    finally:
        conn.close()

    from_str = f"{week_start.day:02d}/{week_start.month:02d}"
    to_str   = f"{week_end.day:02d}/{week_end.month:02d}"
    label    = f"Semana {week} de {year} ({from_str}–{to_str})"
    return {
        "period_type": "weekly",
        "label":       label,
        "date_range":  {"from": week_start.isoformat(), "to": week_end.isoformat()},
        **data,
    }


@router.get("/monthly/{year}/{month}")
def get_monthly_report(year: int, month: int):
    if not 1 <= month <= 12:
        raise HTTPException(400, "Mês inválido.")

    conn = get_db()
    try:
        period_filter = (
            "EXTRACT(YEAR FROM d.assistido_em) = %s "
            "AND EXTRACT(MONTH FROM d.assistido_em) = %s"
        )
        data = _fetch_report_data(conn, period_filter, (year, month))
    finally:
        conn.close()

    if month == 12:
        last_day = 31
    else:
        last_day = (datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)).day

    label = f"{PT_MONTHS[month]} de {year}"
    return {
        "period_type": "monthly",
        "label":       label,
        "date_range":  {"from": f"{year}-{month:02d}-01", "to": f"{year}-{month:02d}-{last_day:02d}"},
        **data,
    }


@router.get("/annual/{year}")
def get_annual_report(year: int):
    conn = get_db()
    try:
        period_filter = "EXTRACT(YEAR FROM d.assistido_em) = %s"
        data = _fetch_report_data(conn, period_filter, (year,))
    finally:
        conn.close()

    return {
        "period_type": "annual",
        "label":       str(year),
        "date_range":  {"from": f"{year}-01-01", "to": f"{year}-12-31"},
        **data,
    }
