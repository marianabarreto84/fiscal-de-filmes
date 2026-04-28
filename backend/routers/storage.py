"""
backend/routers/storage.py

Calcula e persiste o uso de disco da pasta /data.

Endpoints:
  GET  /api/storage           → dados cacheados
  POST /api/storage/calculate → recalcula tudo
"""
from fastapi import APIRouter
from pathlib import Path
import json
import datetime

from backend.database import get_db, dict_cursor

router = APIRouter()

DATA_DIR    = Path(__file__).parent.parent.parent / "data"
IMAGES_DIR  = DATA_DIR / "images"
CONFIG_KEY  = "storage_cache"


def _dir_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _calculate() -> dict:
    conn = get_db()
    try:
        posters_bytes   = _dir_bytes(IMAGES_DIR / "posters")
        backdrops_bytes = _dir_bytes(IMAGES_DIR / "backdrops")
        providers_bytes = _dir_bytes(IMAGES_DIR / "providers")
        images_total    = posters_bytes + backdrops_bytes + providers_bytes
        total_bytes     = images_total

        result = {
            "calculated_at":      datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "total_bytes":        total_bytes,
            "images_total_bytes": images_total,
            "posters_bytes":      posters_bytes,
            "backdrops_bytes":    backdrops_bytes,
            "providers_bytes":    providers_bytes,
        }

        with dict_cursor(conn) as cur:
            cur.execute("""
                INSERT INTO configuracao (chave, valor, atualizado_em)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (chave) DO UPDATE SET
                    valor         = EXCLUDED.valor,
                    atualizado_em = CURRENT_TIMESTAMP
            """, (CONFIG_KEY, json.dumps(result)))
        conn.commit()
        return result
    finally:
        conn.close()


@router.get("")
def get_storage():
    conn = get_db()
    try:
        with dict_cursor(conn) as cur:
            cur.execute("SELECT valor FROM configuracao WHERE chave = %s", (CONFIG_KEY,))
            row = cur.fetchone()
        if not row:
            return None
        return json.loads(row["valor"])
    finally:
        conn.close()


@router.post("/calculate")
def calculate_storage():
    return _calculate()
